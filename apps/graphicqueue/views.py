from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_http_methods
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q

from apps.core.access import system_required
from apps.producttest.models import Employee

from .models import GraphicJob, MediaType, RefImage
from .forms import GraphicJobForm


def _stat_cards(qs_all):
    wait = qs_all.filter(status=GraphicJob.STATUS_WAIT).count()
    prog = qs_all.filter(status=GraphicJob.STATUS_IN_PROGRESS).count()
    done = qs_all.filter(status=GraphicJob.STATUS_DONE).count()
    total = qs_all.count()
    backlog = wait + prog
    return [
        ("คิวงานทั้งหมด",   "ALL",           "bg-secondary",  "fa-layer-group",         total),
        ("รอดำเนินการ",    GraphicJob.STATUS_WAIT,         "bg-secondary",  "fa-clock",               wait),
        ("กำลังดำเนินการ", GraphicJob.STATUS_IN_PROGRESS,  "bg-warning",    "fa-spinner",             prog),
        ("งานที่ค้าง",     "งานที่ค้าง",    "bg-danger",     "fa-triangle-exclamation", backlog),
        ("เรียบร้อย",      GraphicJob.STATUS_DONE,         "bg-success",    "fa-circle-check",        done),
    ]


def _apply_filters(qs, request):
    status = request.GET.get("status", "ALL")
    product_type = request.GET.get("product_type", "ALL")
    assignee_name = request.GET.get("assignee", "ALL")
    month = request.GET.get("month", "")
    search = request.GET.get("q", "").strip()

    if status == "งานที่ค้าง":
        qs = qs.exclude(status=GraphicJob.STATUS_DONE)
    elif status != "ALL":
        qs = qs.filter(status=status)

    if product_type != "ALL":
        qs = qs.filter(product_type=product_type)

    if assignee_name != "ALL":
        qs = qs.filter(assignee__name=assignee_name)

    if month:
        try:
            year, mo = month.split("-")
            qs = qs.filter(order_date__year=int(year), order_date__month=int(mo))
        except ValueError:
            pass

    if search:
        qs = qs.filter(Q(sku__icontains=search) | Q(name__icontains=search))

    return qs


# ── List & table partial ─────────────────────────────────────────────────────

@system_required("graphicqueue")
def queue_list(request):
    all_qs = GraphicJob.objects.all()
    graphic_employees = Employee.objects.filter(is_graphic=True, is_active=True)
    return render(request, "graphicqueue/queue_list.html", {
        "stat_cards": _stat_cards(all_qs),
        "graphic_employees": graphic_employees,
        "current_status": request.GET.get("status", "ALL"),
        "current_product_type": request.GET.get("product_type", "ALL"),
        "current_assignee": request.GET.get("assignee", "ALL"),
        "current_month": request.GET.get("month", ""),
        "current_q": request.GET.get("q", ""),
    })


@system_required("graphicqueue")
def queue_table_partial(request):
    qs = GraphicJob.objects.select_related("assignee").prefetch_related("media_types", "ref_images")
    qs = _apply_filters(qs, request)
    return render(request, "graphicqueue/partials/queue_rows.html", {"jobs": list(qs)})


# ── Add / Edit / Delete ──────────────────────────────────────────────────────

@system_required("graphicqueue")
@require_http_methods(["GET", "POST"])
def queue_form(request, pk=None):
    instance = get_object_or_404(GraphicJob, pk=pk) if pk else None

    if request.method == "POST":
        form = GraphicJobForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            with transaction.atomic():
                job = form.save()

                # Media types M2M
                media_ids = request.POST.getlist("media_type_ids")
                job.media_types.set(MediaType.objects.filter(pk__in=media_ids))

                # Delete selected existing ref images
                delete_ids = request.POST.getlist("delete_ref_ids")
                if delete_ids:
                    job.ref_images.filter(pk__in=delete_ids).delete()

                # Add new ref images (paired with brief texts)
                new_images = request.FILES.getlist("ref_images")
                new_briefs = request.POST.getlist("ref_briefs")
                current_order = job.ref_images.count()
                for i, img in enumerate(new_images):
                    brief = new_briefs[i].strip() if i < len(new_briefs) else ""
                    RefImage.objects.create(job=job, image=img, brief=brief, order=current_order + i)

            if request.htmx:
                return HttpResponse(
                    '<script>htmx.trigger("#queue-table", "refresh")</script>'
                    '<div class="toast-trigger" data-message="บันทึกสำเร็จ"></div>'
                )
            return redirect("graphicqueue:queue_list")
    else:
        form = GraphicJobForm(instance=instance)

    checked_ids = set(instance.media_types.values_list("pk", flat=True)) if instance else set()
    video_types = MediaType.objects.filter(category=MediaType.CATEGORY_VIDEO).order_by("order", "id")
    image_types = MediaType.objects.filter(category=MediaType.CATEGORY_IMAGE).order_by("order", "id")
    existing_refs = list(instance.ref_images.all()) if instance else []

    return render(request, "graphicqueue/partials/queue_form_modal.html", {
        "form": form,
        "instance": instance,
        "checked_ids": checked_ids,
        "video_types": video_types,
        "image_types": image_types,
        "existing_refs": existing_refs,
    })


@system_required("graphicqueue")
@require_POST
def queue_delete(request, pk):
    job = get_object_or_404(GraphicJob, pk=pk)
    job.delete()
    if request.htmx:
        return HttpResponse(
            '<script>htmx.trigger("#queue-table", "refresh")</script>'
            '<div class="toast-trigger" data-message="ลบคิวงานเรียบร้อย" data-type="info"></div>'
        )
    return redirect("graphicqueue:queue_list")


# ── Media type management ────────────────────────────────────────────────────

@system_required("graphicqueue")
def media_options(request):
    """Return the checkbox partial (used on initial form load)."""
    checked_ids = set(int(x) for x in request.GET.getlist("checked") if x.isdigit())
    video_types = MediaType.objects.filter(category=MediaType.CATEGORY_VIDEO).order_by("order", "id")
    image_types = MediaType.objects.filter(category=MediaType.CATEGORY_IMAGE).order_by("order", "id")
    return render(request, "graphicqueue/partials/media_options.html", {
        "video_types": video_types,
        "image_types": image_types,
        "checked_ids": checked_ids,
    })


@system_required("graphicqueue")
@require_POST
def media_type_add(request):
    """Create a new MediaType from freetext, return updated checkbox list."""
    name = request.POST.get("new_type_name", "").strip()
    category = request.POST.get("new_type_category", MediaType.CATEGORY_VIDEO)
    checked_str = request.POST.getlist("media_type_ids")
    checked_ids = set(int(x) for x in checked_str if x.isdigit())

    if name:
        order = MediaType.objects.filter(category=category).count()
        mtype, _ = MediaType.objects.get_or_create(
            name=name,
            defaults={"category": category, "order": order},
        )
        checked_ids.add(mtype.pk)

    video_types = MediaType.objects.filter(category=MediaType.CATEGORY_VIDEO).order_by("order", "id")
    image_types = MediaType.objects.filter(category=MediaType.CATEGORY_IMAGE).order_by("order", "id")
    return render(request, "graphicqueue/partials/media_options.html", {
        "video_types": video_types,
        "image_types": image_types,
        "checked_ids": checked_ids,
    })


# ── View-only modals ─────────────────────────────────────────────────────────

@system_required("graphicqueue")
def view_media_modal(request, pk):
    job = get_object_or_404(GraphicJob, pk=pk)
    video_media = job.media_types.filter(category=MediaType.CATEGORY_VIDEO)
    image_media = job.media_types.filter(category=MediaType.CATEGORY_IMAGE)
    return render(request, "graphicqueue/partials/view_media_modal.html", {
        "job": job,
        "video_media": video_media,
        "image_media": image_media,
    })


@system_required("graphicqueue")
def view_ref_modal(request, pk):
    job = get_object_or_404(GraphicJob, pk=pk)
    return render(request, "graphicqueue/partials/view_ref_modal.html", {
        "job": job,
        "refs": list(job.ref_images.all()),
    })
