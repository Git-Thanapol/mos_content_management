from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST, require_http_methods

from apps.clearance.jst import enrich, search_products
from apps.core.access import system_required
from apps.producttest.models import Employee

from .forms import FacebookPageForm, PagePostForm
from .models import FacebookPage, PagePost, PageSKU, PostMediaType
from .scoping import is_supervisor, visible_pages


def _stat_cards(qs):
    total = qs.count()
    cards = [("ทั้งหมด", "ALL", "bg-secondary", "fa-list", total)]
    colors = {
        FacebookPage.STATUS_NEW: ("bg-danger", "fa-star"),
        FacebookPage.STATUS_ACTIVE: ("bg-success", "fa-bolt"),
        FacebookPage.STATUS_NON_ACTIVE: ("bg-warning", "fa-pause"),
        FacebookPage.STATUS_OLD: ("bg-info", "fa-clock-rotate-left"),
        FacebookPage.STATUS_SOLD_OUT: ("bg-primary", "fa-box-open"),
        FacebookPage.STATUS_DISCONTINUED: ("bg-dark", "fa-ban"),
    }
    for value, label in FacebookPage.STATUS_CHOICES:
        color, icon = colors.get(value, ("bg-secondary", "fa-circle"))
        cards.append((label, value, color, icon, qs.filter(status=value).count()))
    return cards


def _apply_page_filters(qs, request):
    status = request.GET.get("status", "ALL")
    sku = request.GET.get("sku", "").strip()
    page_name = request.GET.get("page_name", "").strip()
    page_id = request.GET.get("page_id", "").replace(" ", "").strip()

    if status != "ALL":
        qs = qs.filter(status=status)
    if sku:
        qs = qs.filter(skus__product_code__icontains=sku).distinct()
    if page_name:
        qs = qs.filter(page_name__icontains=page_name)
    if page_id:
        qs = qs.filter(page_id__icontains=page_id)
    return qs


# ── Pages: list & table partial ──────────────────────────────────────────────

@system_required("pagemanager")
def page_list(request):
    scoped = visible_pages(request.user)
    return render(request, "pagemanager/page_list.html", {
        "stat_cards": _stat_cards(scoped),
        "is_supervisor": is_supervisor(request.user),
        "current_status": request.GET.get("status", "ALL"),
        "current_sku": request.GET.get("sku", ""),
        "current_page_name": request.GET.get("page_name", ""),
        "current_page_id": request.GET.get("page_id", ""),
    })


@system_required("pagemanager")
def page_table_partial(request):
    qs = visible_pages(request.user).prefetch_related("skus", "owners").annotate(
        post_count=Count("posts", distinct=True)
    )
    qs = _apply_page_filters(qs, request)
    return render(request, "pagemanager/partials/page_rows.html", {
        "pages": list(qs),
        "is_supervisor": is_supervisor(request.user),
    })


# ── Pages: add / edit / delete (supervisor only) ─────────────────────────────

@system_required("pagemanager")
@user_passes_test(is_supervisor)
@require_http_methods(["GET", "POST"])
def page_form(request, pk=None):
    instance = get_object_or_404(visible_pages(request.user), pk=pk) if pk else None

    if request.method == "POST":
        form = FacebookPageForm(request.POST, instance=instance)
        if form.is_valid():
            with transaction.atomic():
                page = form.save()

                codes = [c.strip() for c in request.POST.getlist("sku_code") if c.strip()]
                names = request.POST.getlist("sku_name")
                jst_data = enrich(codes) if codes else {}
                page.skus.all().delete()
                for i, code in enumerate(codes):
                    fresh_name = jst_data.get(code, {}).get("name", "")
                    fallback_name = names[i] if i < len(names) else ""
                    PageSKU.objects.create(
                        page=page,
                        product_code=code,
                        product_name=fresh_name if fresh_name and fresh_name != "-" else fallback_name,
                        order=i,
                    )

            if request.htmx:
                return HttpResponse(
                    '<script>htmx.trigger("#page-table", "refresh")</script>'
                    '<div class="toast-trigger" data-message="บันทึกสำเร็จ"></div>'
                )
            return redirect("pagemanager:page_list")
    else:
        form = FacebookPageForm(instance=instance)

    existing_skus = list(instance.skus.all()) if instance else []
    return render(request, "pagemanager/partials/page_form_modal.html", {
        "form": form,
        "instance": instance,
        "existing_skus": existing_skus,
    })


@system_required("pagemanager")
@user_passes_test(is_supervisor)
@require_POST
def page_delete(request, pk):
    page = get_object_or_404(visible_pages(request.user), pk=pk)
    page.delete()
    if request.htmx:
        return HttpResponse(
            '<script>htmx.trigger("#page-table", "refresh")</script>'
            '<div class="toast-trigger" data-message="ลบเพจเรียบร้อย" data-type="info"></div>'
        )
    return redirect("pagemanager:page_list")


# ── JST SKU search ────────────────────────────────────────────────────────────

@system_required("pagemanager")
def jst_search(request):
    q = request.GET.get("q", "").strip()
    items = search_products(q, limit=20) if q else []
    return render(request, "pagemanager/partials/jst_options.html", {"items": items, "q": q})


# ── Posts: list & table partial ──────────────────────────────────────────────

@system_required("pagemanager")
def post_list(request, page_pk):
    page = get_object_or_404(visible_pages(request.user), pk=page_pk)
    return render(request, "pagemanager/post_list.html", {
        "page": page,
        "is_supervisor": is_supervisor(request.user),
        "posters": Employee.objects.filter(is_active=True, user__isnull=False),
        "media_types": PostMediaType.objects.all(),
        "current_poster": request.GET.get("poster", "ALL"),
        "current_media_type": request.GET.get("media_type", "ALL"),
        "current_date_from": request.GET.get("date_from", ""),
        "current_date_to": request.GET.get("date_to", ""),
        "current_q": request.GET.get("q", ""),
    })


@system_required("pagemanager")
def post_table_partial(request, page_pk):
    page = get_object_or_404(visible_pages(request.user), pk=page_pk)
    qs = page.posts.select_related("poster", "media_type")

    poster = request.GET.get("poster", "ALL")
    media_type = request.GET.get("media_type", "ALL")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    search = request.GET.get("q", "").strip()

    if poster != "ALL":
        qs = qs.filter(poster_id=poster)
    if media_type != "ALL":
        qs = qs.filter(media_type_id=media_type)
    if date_from:
        d = parse_date(date_from)
        if d:
            qs = qs.filter(post_date__gte=d)
    if date_to:
        d = parse_date(date_to)
        if d:
            qs = qs.filter(post_date__lte=d)
    if search:
        qs = qs.filter(Q(post_id__icontains=search) | Q(product_code__icontains=search))

    return render(request, "pagemanager/partials/post_rows.html", {
        "posts": list(qs),
        "page": page,
        "is_supervisor": is_supervisor(request.user),
    })


# ── Posts: add / edit / delete ───────────────────────────────────────────────

@system_required("pagemanager")
@require_http_methods(["GET", "POST"])
def post_form(request, page_pk, pk=None):
    page = get_object_or_404(visible_pages(request.user), pk=page_pk)
    instance = get_object_or_404(PagePost, pk=pk, page=page) if pk else None
    sup = is_supervisor(request.user)

    if request.method == "POST":
        form = PagePostForm(request.POST, request.FILES, instance=instance, is_supervisor=sup)
        if form.is_valid():
            post = form.save(commit=False)
            post.page = page
            if post.product_code:
                jst_result = enrich([post.product_code])
                fresh_name = jst_result.get(post.product_code, {}).get("name", "")
                if fresh_name and fresh_name != "-":
                    post.product_name = fresh_name
            post.save()

            if request.htmx:
                return HttpResponse(
                    '<script>htmx.trigger("#post-table", "refresh")</script>'
                    '<div class="toast-trigger" data-message="บันทึกสำเร็จ"></div>'
                )
            return redirect("pagemanager:post_list", page_pk=page.pk)
    else:
        form = PagePostForm(instance=instance, is_supervisor=sup)

    return render(request, "pagemanager/partials/post_form_modal.html", {
        "form": form,
        "instance": instance,
        "page": page,
        "is_supervisor": sup,
    })


@system_required("pagemanager")
@require_POST
def post_delete(request, page_pk, pk):
    page = get_object_or_404(visible_pages(request.user), pk=page_pk)
    post = get_object_or_404(PagePost, pk=pk, page=page)
    post.delete()
    if request.htmx:
        return HttpResponse(
            '<script>htmx.trigger("#post-table", "refresh")</script>'
            '<div class="toast-trigger" data-message="ลบโพสต์เรียบร้อย" data-type="info"></div>'
        )
    return redirect("pagemanager:post_list", page_pk=page.pk)


# ── Media type management ────────────────────────────────────────────────────

@system_required("pagemanager")
@require_POST
def media_type_add(request):
    name = request.POST.get("new_type_name", "").strip()
    selected = request.POST.get("media_type", "")
    if name:
        order = PostMediaType.objects.count()
        mtype, _ = PostMediaType.objects.get_or_create(name=name, defaults={"order": order})
        selected = str(mtype.pk)
    return render(request, "pagemanager/partials/media_type_select.html", {
        "media_types": PostMediaType.objects.all(),
        "selected": selected,
    })
