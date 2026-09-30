from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db.models import Count, DecimalField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST, require_http_methods

from apps.clearance.jst import enrich, search_products
from apps.core.access import system_required
from apps.producttest.models import Employee

from .forms import FacebookPageForm, PagePostForm
from .models import (
    FacebookPage, PageAds, PageCategory, PagePost, PageSKU, PageStockItem, PostMediaType,
)
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


def _jst_stock_total(codes, jst_data):
    total = 0
    for c in codes:
        stock = jst_data.get(c, {}).get("stock")
        if isinstance(stock, (int, float, Decimal)):
            total += stock
    return total


@system_required("pagemanager")
def page_table_partial(request):
    ads_sum = (
        PageAds.objects.filter(page=OuterRef("pk")).values("page")
        .annotate(t=Sum("amount")).values("t")
    )
    qs = visible_pages(request.user).select_related("category").prefetch_related(
        "skus", "owners", "stock_items"
    ).annotate(
        post_count=Count("posts", distinct=True),
        ads_total=Coalesce(Subquery(ads_sum, output_field=DecimalField()), Decimal("0")),
    )
    qs = _apply_page_filters(qs, request)
    pages = list(qs)

    codes = {i.product_code for p in pages for i in p.stock_items.all()}
    jst_data = enrich(sorted(codes)) if codes else {}
    for p in pages:
        p.stock_total = _jst_stock_total({i.product_code for i in p.stock_items.all()}, jst_data)

    resp = render(request, "pagemanager/partials/page_rows.html", {
        "pages": pages,
        "categories": PageCategory.objects.all(),
        "is_supervisor": is_supervisor(request.user),
    })
    # Hero total follows the visible + filtered pages; the JS listener in page_list.html renders it
    grand_total = sum((p.ads_total for p in pages), Decimal("0"))
    resp["HX-Trigger"] = json.dumps({"ads-total": f"฿{grand_total:,.2f}"})
    return resp


@system_required("pagemanager")
@require_POST
def page_category_set(request, pk):
    page = get_object_or_404(visible_pages(request.user), pk=pk)
    cat_id = request.POST.get("category", "")
    page.category = PageCategory.objects.filter(pk=cat_id).first() if cat_id else None
    page.save(update_fields=["category", "updated_at"])
    return HttpResponse('<div class="toast-trigger" data-message="อัปเดตหมวดหมู่เรียบร้อย"></div>')


# ── Categories (supervisor only) ─────────────────────────────────────────────

def _category_modal(request, body=False):
    tpl = "category_body" if body else "category_modal"
    return render(request, f"pagemanager/partials/{tpl}.html", {
        "categories": PageCategory.objects.annotate(n=Count("pages")),
    })


@system_required("pagemanager")
@user_passes_test(is_supervisor)
def category_modal(request):
    return _category_modal(request)


@system_required("pagemanager")
@user_passes_test(is_supervisor)
@require_POST
def category_add(request):
    name = request.POST.get("name", "").strip()
    if name:
        PageCategory.objects.get_or_create(name=name, defaults={"order": PageCategory.objects.count()})
    return _category_modal(request, body=True)


@system_required("pagemanager")
@user_passes_test(is_supervisor)
@require_POST
def category_delete(request, pk):
    PageCategory.objects.filter(pk=pk).delete()  # pages fall back to null = "ไม่ระบุ"
    resp = _category_modal(request, body=True)
    resp["HX-Trigger"] = "pages-changed"
    return resp


# ── Monthly ADS ──────────────────────────────────────────────────────────────

def _ads_modal(request, page, body=False):
    ads = list(page.ads.all())
    tpl = "ads_body" if body else "ads_modal"
    return render(request, f"pagemanager/partials/{tpl}.html", {
        "page": page,
        "ads": ads,
        "ads_total": sum((a.amount for a in ads), Decimal("0")),
        "default_month": date.today().strftime("%Y-%m"),
    })


@system_required("pagemanager")
def ads_modal(request, pk):
    return _ads_modal(request, get_object_or_404(visible_pages(request.user), pk=pk))


@system_required("pagemanager")
@require_POST
def ads_save(request, pk):
    page = get_object_or_404(visible_pages(request.user), pk=pk)
    try:
        y, m = request.POST.get("month", "").split("-")
        month = date(int(y), int(m), 1)
        amount = Decimal(request.POST.get("amount", "0") or "0")
        if amount < 0:
            raise InvalidOperation
    except (ValueError, InvalidOperation):
        return HttpResponse("ข้อมูลไม่ถูกต้อง", status=400)
    PageAds.objects.update_or_create(page=page, month=month, defaults={"amount": amount})
    resp = _ads_modal(request, page, body=True)
    resp["HX-Trigger"] = "pages-changed"
    return resp


@system_required("pagemanager")
@require_POST
def ads_delete(request, pk, ads_pk):
    page = get_object_or_404(visible_pages(request.user), pk=pk)
    PageAds.objects.filter(pk=ads_pk, page=page).delete()
    resp = _ads_modal(request, page, body=True)
    resp["HX-Trigger"] = "pages-changed"
    return resp


# ── STOCK sub-page (qty read live from JST) ──────────────────────────────────

def _stock_context(page):
    items = list(page.stock_items.all())
    sku_codes = [s.product_code for s in page.skus.all()]
    codes = sorted({i.product_code for i in items})
    jst_data = enrich(codes) if codes else {}
    rows = [
        {"item": it, "stock": jst_data.get(it.product_code, {}).get("stock", "-")}
        for it in items
    ]
    # dropdown = page SKUs plus codes already used by rows (rows are kept when a SKU is removed)
    options = list(dict.fromkeys(sku_codes + [i.product_code for i in items]))
    return {
        "page": page,
        "rows": rows,
        "sku_options": options,
        "total_qty": _jst_stock_total(codes, jst_data),
        "unique_skus": len(codes),
    }


@system_required("pagemanager")
def stock_list(request, pk):
    page = get_object_or_404(visible_pages(request.user), pk=pk)
    return render(request, "pagemanager/stock_list.html", _stock_context(page))


@system_required("pagemanager")
def stock_body(request, pk):
    page = get_object_or_404(visible_pages(request.user), pk=pk)
    return render(request, "pagemanager/partials/stock_body.html", _stock_context(page))


@system_required("pagemanager")
@require_POST
def stock_add(request, pk):
    page = get_object_or_404(visible_pages(request.user), pk=pk)
    code = request.POST.get("product_code", "").strip()
    if code:
        PageStockItem.objects.create(page=page, product_code=code)
    return render(request, "pagemanager/partials/stock_body.html", _stock_context(page))


@system_required("pagemanager")
@require_POST
def stock_update(request, pk, item_pk):
    page = get_object_or_404(visible_pages(request.user), pk=pk)
    item = get_object_or_404(PageStockItem, pk=item_pk, page=page)
    code = request.POST.get("product_code", "").strip()
    if code:
        item.product_code = code
    if "note" in request.POST:
        item.note = request.POST["note"].strip()
    item.save()
    return render(request, "pagemanager/partials/stock_body.html", _stock_context(page))


@system_required("pagemanager")
@require_POST
def stock_delete(request, pk, item_pk):
    page = get_object_or_404(visible_pages(request.user), pk=pk)
    PageStockItem.objects.filter(pk=item_pk, page=page).delete()
    return render(request, "pagemanager/partials/stock_body.html", _stock_context(page))


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
