import json

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_http_methods
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date

from apps.core.access import system_required
from .models import ClearanceProduct, ClearancePromo
from .forms import ClearanceProductForm
from . import jst


# ── List & table partial ─────────────────────────────────────────────────────

@system_required("clearance")
def clearance_list(request):
    qs = ClearanceProduct.objects
    stats = {
        "all": qs.count(),
        "wait": qs.filter(status=ClearanceProduct.STATUS_WAIT).count(),
        "progress": qs.filter(status=ClearanceProduct.STATUS_IN_PROGRESS).count(),
        "done": qs.filter(status=ClearanceProduct.STATUS_DONE).count(),
    }
    stat_cards = [
        ("ทั้งหมด (โล๊ะ)", "ALL",          "bg-secondary", "fa-list",             stats["all"]),
        ("รอดำเนินการ",    ClearanceProduct.STATUS_WAIT,         "bg-primary",   "fa-clock-rotate-left", stats["wait"]),
        ("กำลังดำเนินการ", ClearanceProduct.STATUS_IN_PROGRESS,  "bg-warning",   "fa-hourglass-half",    stats["progress"]),
        ("เรียบร้อย",      ClearanceProduct.STATUS_DONE,         "bg-success",   "fa-circle-check",      stats["done"]),
    ]
    return render(request, "clearance/clearance_list.html", {
        "stat_cards": stat_cards,
        "stats": stats,
        "current_status": request.GET.get("status", "ALL"),
        "current_q": request.GET.get("q", ""),
    })


@system_required("clearance")
def clearance_table_partial(request):
    status_filter = request.GET.get("status", "ALL")
    search = request.GET.get("q", "").strip()

    qs = ClearanceProduct.objects.prefetch_related("promos")

    if status_filter != "ALL":
        qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(
            Q(product_code__icontains=search) | Q(product_name__icontains=search)
        )

    products = list(qs)
    codes = [p.product_code for p in products if p.product_code]
    jst_data = jst.enrich(codes) if codes else {}

    # Merge JST data into each product row so templates don't need dict-key filters
    rows = []
    for p in products:
        d = jst_data.get(p.product_code, {})
        rows.append({
            "product": p,
            "jst_name": d.get("name", p.product_name or "-"),
            "jst_stock": d.get("stock", "-"),
            "jst_cost": d.get("cost", "-"),
            "jst_last_order_date": d.get("last_order_date"),
            "jst_image": d.get("image", ""),
        })

    return render(request, "clearance/partials/clearance_rows.html", {"rows": rows})


# ── Add / Edit / Delete ──────────────────────────────────────────────────────

@system_required("clearance")
@require_http_methods(["GET", "POST"])
def clearance_form(request, pk=None):
    instance = get_object_or_404(ClearanceProduct, pk=pk) if pk else None

    if request.method == "POST":
        form = ClearanceProductForm(request.POST, instance=instance)
        if form.is_valid():
            product = form.save(commit=False)
            # Always try to refresh name cache from JST
            if product.product_code:
                jst_result = jst.enrich([product.product_code])
                fresh_name = jst_result.get(product.product_code, {}).get("name", "")
                if fresh_name and fresh_name != "-":
                    product.product_name = fresh_name
            product.save()

            if request.htmx:
                return HttpResponse(
                    '<script>htmx.trigger("#clearance-table", "refresh")</script>'
                    '<div class="toast-trigger" data-message="บันทึกสำเร็จ"></div>'
                )
            return redirect("clearance:clearance_list")
    else:
        form = ClearanceProductForm(instance=instance)

    # Pre-populate JST info for the edit case
    jst_info = None
    if instance and instance.product_code:
        jst_result = jst.enrich([instance.product_code])
        jst_info = jst_result.get(instance.product_code)

    return render(request, "clearance/partials/clearance_form_modal.html", {
        "form": form,
        "instance": instance,
        "jst_info": jst_info,
    })


@system_required("clearance")
@require_POST
def clearance_delete(request, pk):
    product = get_object_or_404(ClearanceProduct, pk=pk)
    product.delete()
    if request.htmx:
        return HttpResponse(
            '<script>htmx.trigger("#clearance-table", "refresh")</script>'
            '<div class="toast-trigger" data-message="ลบสินค้าเรียบร้อย" data-type="info"></div>'
        )
    return redirect("clearance:clearance_list")


# ── Promo modal ──────────────────────────────────────────────────────────────

@system_required("clearance")
@require_http_methods(["GET", "POST"])
def promo_modal(request, pk):
    product = get_object_or_404(ClearanceProduct, pk=pk)

    if request.method == "POST":
        promos_json = request.POST.get("promos_json", "[]")
        try:
            promos_data = json.loads(promos_json)
        except (json.JSONDecodeError, ValueError):
            promos_data = []

        with transaction.atomic():
            product.promos.all().delete()
            for i, row in enumerate(promos_data):
                old_price = str(row.get("old", "")).strip()
                new_price = str(row.get("new", "")).strip()
                if old_price or new_price:
                    ClearancePromo.objects.create(
                        product=product,
                        old_price=old_price,
                        new_price=new_price,
                        order=i,
                    )

        if request.htmx:
            return HttpResponse(
                '<script>htmx.trigger("#clearance-table", "refresh")</script>'
                '<div class="toast-trigger" data-message="อัปเดตโปรโมชั่นสำเร็จ"></div>'
            )
        return redirect("clearance:clearance_list")

    return render(request, "clearance/partials/promo_modal.html", {
        "product": product,
        "promos": list(product.promos.values("old_price", "new_price")),
    })


# ── JST HTMX helpers ─────────────────────────────────────────────────────────

@system_required("clearance")
def jst_search(request):
    """Return a list of JST SKU options matching the search query (HTMX only)."""
    q = request.GET.get("q", "").strip()
    items = jst.search_products(q, limit=20) if q else []
    return render(request, "clearance/partials/jst_options.html", {"items": items, "q": q})


@system_required("clearance")
def jst_fields(request):
    """Return a read-only info block for a given JST product code (HTMX only)."""
    code = request.GET.get("code", "").strip()
    info = None
    if code:
        result = jst.enrich([code])
        info = result.get(code)
    return render(request, "clearance/partials/jst_fields.html", {
        "code": code,
        "info": info,
    })
