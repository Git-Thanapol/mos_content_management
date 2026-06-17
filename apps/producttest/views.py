import json
import secrets
import string
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST, require_http_methods
from django.http import HttpResponse
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.core.access import system_required

from .models import (
    Employee, TestProduct, TestPrice, ProductPage,
    Performance, Commission, CommissionSlip,
)
from .forms import (
    EmployeeForm, TestProductForm,
    PerformanceForm, CommissionForm, DateRangeForm,
)


def is_supervisor(user):
    return user.groups.filter(name="supervisor").exists()


def _generate_pid():
    """Generate a unique 7-char alphanumeric Product ID (uppercase A-Z + 0-9)."""
    chars = string.ascii_uppercase + string.digits
    for _ in range(20):  # at most 20 attempts
        pid = "".join(secrets.choice(chars) for _ in range(7))
        if not TestProduct.objects.filter(pid=pid).exists():
            return pid
    return "".join(secrets.choice(chars) for _ in range(7))  # fallback


def _get_products_qs(request):
    """Return filtered TestProduct queryset based on GET params."""
    qs = TestProduct.objects.prefetch_related(
        "graphic_members", "mkt_members", "prices", "pages"
    ).select_related("performance", "commission")

    status = request.GET.get("status", "ALL")
    employee = request.GET.get("employee", "ALL")
    search = request.GET.get("q", "").strip()
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if employee != "ALL":
        from django.db.models import Q
        qs = qs.filter(
            Q(graphic_members__name=employee) |
            Q(mkt_members__name=employee)
        ).distinct()

    if search:
        from django.db.models import Q
        qs = qs.filter(Q(pid__icontains=search) | Q(name__icontains=search))

    if date_from:
        d = parse_date(date_from)
        if d:
            qs = qs.filter(upload_date__gte=d)
    if date_to:
        d = parse_date(date_to)
        if d:
            qs = qs.filter(upload_date__lte=d)

    # Annotate computed status then filter (done in Python to reuse the method)
    products = list(qs)
    if status != "ALL":
        products = [p for p in products if p.computed_status() == status]

    return products, qs


def _product_stats(qs):
    all_products = list(qs)
    stats = {"all": len(all_products), "wait": 0, "prog": 0, "pass": 0, "fail": 0, "canc": 0}
    key_map = {
        "รอดำเนินการ": "wait",
        "กำลังดำเนินการ": "prog",
        "Test ผ่าน": "pass",
        "Test ไม่ผ่าน": "fail",
        "ยกเลิก": "canc",
    }
    for p in all_products:
        k = key_map.get(p.computed_status())
        if k:
            stats[k] += 1
    return stats


# ── Product List ──────────────────────────────────────────────────────────────

@system_required("producttest")
def product_list(request):
    qs = TestProduct.objects.prefetch_related("graphic_members", "mkt_members")
    stats = _product_stats(qs)
    employees = Employee.objects.filter(is_active=True)
    date_form = DateRangeForm(request.GET or None)
    stat_cards = [
        ("ทั้งหมด",         "ALL",              "bg-primary",  "fa-boxes-stacked",     stats["all"]),
        ("รอดำเนินการ",     "รอดำเนินการ",      "bg-secondary",  "fa-clock-rotate-left", stats["wait"]),
        ("กำลังดำเนินการ",  "กำลังดำเนินการ",   "bg-warning",    "fa-spinner",           stats["prog"]),
        ("Test ผ่าน",       "Test ผ่าน",         "bg-success",    "fa-circle-check",      stats["pass"]),
        ("Test ไม่ผ่าน",    "Test ไม่ผ่าน",      "bg-danger",     "fa-circle-xmark",      stats["fail"]),
        ("ยกเลิก",          "ยกเลิก",            "bg-dark",       "fa-ban",               stats["canc"]),
    ]
    context = {
        "stats": stats,
        "stat_cards": stat_cards,
        "employees": employees,
        "date_form": date_form,
        "is_supervisor": is_supervisor(request.user),
        "current_status": request.GET.get("status", "ALL"),
        "current_employee": request.GET.get("employee", "ALL"),
        "current_q": request.GET.get("q", ""),
        "current_date_field": request.GET.get("date_field", "upload_date"),
    }
    return render(request, "producttest/product_list.html", context)


@system_required("producttest")
def product_table_partial(request):
    from django.db.models import Q
    qs = TestProduct.objects.prefetch_related(
        "graphic_members", "mkt_members", "prices", "pages"
    ).select_related("performance", "commission")

    status = request.GET.get("status", "ALL")
    employee = request.GET.get("employee", "ALL")
    search = request.GET.get("q", "").strip()
    date_field = request.GET.get("date_field", "upload_date")
    if date_field not in {"upload_date", "start_date"}:
        date_field = "upload_date"
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if employee != "ALL":
        qs = qs.filter(
            Q(graphic_members__name=employee) | Q(mkt_members__name=employee)
        ).distinct()
    if search:
        qs = qs.filter(Q(pid__icontains=search) | Q(name__icontains=search))
    if date_from:
        d = parse_date(date_from)
        if d:
            qs = qs.filter(**{f"{date_field}__gte": d})
    if date_to:
        d = parse_date(date_to)
        if d:
            qs = qs.filter(**{f"{date_field}__lte": d})

    products = list(qs)
    if status != "ALL":
        products = [p for p in products if p.computed_status() == status]

    return render(request, "producttest/partials/product_rows.html", {
        "products": products,
        "is_supervisor": is_supervisor(request.user),
    })


# ── Product Add / Edit ────────────────────────────────────────────────────────

@system_required("producttest")
@require_http_methods(["GET", "POST"])
def product_form(request, pk=None):
    instance = get_object_or_404(TestProduct, pk=pk) if pk else None
    sup = is_supervisor(request.user)

    if request.method == "POST":
        form = TestProductForm(
            request.POST, request.FILES, instance=instance, is_supervisor=sup
        )
        if form.is_valid():
            with transaction.atomic():
                product = form.save()
                # Ensure performance and commission records exist
                Performance.objects.get_or_create(product=product)
                Commission.objects.get_or_create(product=product)

                # Handle dynamic price rows (JSON from hidden input)
                prices_json = request.POST.get("prices_json", "[]")
                try:
                    prices_data = json.loads(prices_json)
                except (json.JSONDecodeError, ValueError):
                    prices_data = []
                product.prices.all().delete()
                for i, val in enumerate(prices_data):
                    v = str(val).strip()
                    if v:
                        TestPrice.objects.create(product=product, value=v, order=i)

                # Handle dynamic page rows (JSON from hidden input)
                pages_json = request.POST.get("pages_json", "[]")
                try:
                    pages_data = json.loads(pages_json)
                except (json.JSONDecodeError, ValueError):
                    pages_data = []
                product.pages.all().delete()
                for i, row in enumerate(pages_data):
                    page = str(row.get("page", "")).strip()
                    url = str(row.get("url", "")).strip()
                    if page or url:
                        ProductPage.objects.create(product=product, page=page, url=url, order=i)

            if request.htmx:
                return HttpResponse(
                    '<script>htmx.trigger("#product-table", "refresh")</script>'
                    '<div class="toast-trigger" data-message="บันทึกสำเร็จ"></div>'
                )
            return redirect("product_list")
    else:
        initial = {}
        if instance is None:
            initial["pid"] = _generate_pid()
        form = TestProductForm(instance=instance, is_supervisor=sup, initial=initial)

    return render(request, "producttest/partials/product_form_modal.html", {
        "form": form,
        "instance": instance,
        "prices": list(instance.prices.values("value", "order")) if instance else [],
        "pages": list(instance.pages.values("page", "url", "order")) if instance else [],
    })


@system_required("producttest")
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(TestProduct, pk=pk)
    product.delete()
    if request.htmx:
        return HttpResponse(
            '<script>htmx.trigger("#product-table", "refresh")</script>'
        )
    return redirect("product_list")


# ── Prices & Pages quick-save ─────────────────────────────────────────────────

@system_required("producttest")
@require_http_methods(["GET", "POST"])
def product_prices(request, pk):
    product = get_object_or_404(TestProduct, pk=pk)
    if request.method == "POST":
        prices_json = request.POST.get("prices_json", "[]")
        try:
            data = json.loads(prices_json)
        except (json.JSONDecodeError, ValueError):
            data = []
        with transaction.atomic():
            product.prices.all().delete()
            for i, val in enumerate(data):
                v = str(val).strip()
                if v:
                    TestPrice.objects.create(product=product, value=v, order=i)
        if request.htmx:
            return HttpResponse(
                '<div class="toast-trigger" data-message="บันทึกราคาสำเร็จ"></div>'
            )
        return redirect("product_list")
    return render(request, "producttest/partials/prices_modal.html", {
        "product": product,
        "prices": list(product.prices.values("value")),
    })


@system_required("producttest")
def product_pages(request, pk):
    """Read-only PAGE viewer — matches mockup's openPageModal."""
    product = get_object_or_404(TestProduct, pk=pk)
    return render(request, "producttest/partials/pages_modal.html", {
        "product": product,
        "pages": list(product.pages.values("page", "url")),
    })


@system_required("producttest")
def product_info(request, pk):
    """Read-only info/media viewer popup."""
    product = get_object_or_404(TestProduct, pk=pk)
    return render(request, "producttest/partials/info_modal.html", {
        "product": product,
    })


# ── Supervisor ────────────────────────────────────────────────────────────────

@system_required("producttest")
@user_passes_test(is_supervisor)
def supervisor_view(request):
    from django.db.models import Sum, Q
    qs = TestProduct.objects.prefetch_related(
        "graphic_members", "mkt_members", "prices", "pages"
    ).select_related("performance", "commission")

    total_paid = Commission.objects.filter(status=Commission.STATUS_PAID).aggregate(
        t=Sum("total")
    )["t"] or 0

    stats = {
        "all": qs.count(),
        "wait_fill": Commission.objects.filter(status=Commission.STATUS_WAIT_FILL).count(),
        "wait_pay": Commission.objects.filter(status=Commission.STATUS_WAIT_PAY).count(),
        "paid": Commission.objects.filter(status=Commission.STATUS_PAID).count(),
        "failed": Commission.objects.filter(status=Commission.STATUS_FAILED).count(),
        "total_paid": total_paid,
    }
    employees = Employee.objects.filter(is_active=True)
    date_form = DateRangeForm(request.GET or None)

    sup_stat_cards = [
        ("ทั้งหมด",              "ALL",                   "bg-primary",   "fa-layer-group",    stats["all"]),
        ("รอกรอกค่าคอม",        "รอกรอกค่าคอม",          "bg-secondary", "fa-file-pen",       stats["wait_fill"]),
        ("รอจ่ายค่าคอม",        "รอจ่ายค่าคอม",          "bg-info",      "fa-hourglass-half", stats["wait_pay"]),
        ("จ่ายค่าคอมเรียบร้อย", "จ่ายค่าคอมเรียบร้อย",  "bg-success",   "fa-money-bill-wave",stats["paid"]),
        ("ไม่ผ่าน",              "ไม่ผ่าน",               "bg-danger",    "fa-ban",            stats["failed"]),
    ]
    return render(request, "producttest/supervisor.html", {
        "stats": stats,
        "sup_stat_cards": sup_stat_cards,
        "employees": employees,
        "date_form": date_form,
        "current_status": request.GET.get("status", "ALL"),
        "current_employee": request.GET.get("employee", "ALL"),
        "current_q": request.GET.get("q", ""),
        "current_date_field": request.GET.get("date_field", "upload_date"),
    })


@system_required("producttest")
@user_passes_test(is_supervisor)
def supervisor_table_partial(request):
    from django.db.models import Q
    qs = TestProduct.objects.prefetch_related(
        "graphic_members", "mkt_members", "prices", "pages"
    ).select_related("performance", "commission")

    comm_status = request.GET.get("status", "ALL")
    employee = request.GET.get("employee", "ALL")
    search = request.GET.get("q", "").strip()
    date_field = request.GET.get("date_field", "upload_date")
    if date_field not in {"upload_date", "start_date"}:
        date_field = "upload_date"
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if employee != "ALL":
        qs = qs.filter(
            Q(graphic_members__name=employee) | Q(mkt_members__name=employee)
        ).distinct()
    if search:
        qs = qs.filter(Q(pid__icontains=search) | Q(name__icontains=search))
    if date_from:
        d = parse_date(date_from)
        if d:
            qs = qs.filter(**{f"{date_field}__gte": d})
    if date_to:
        d = parse_date(date_to)
        if d:
            qs = qs.filter(**{f"{date_field}__lte": d})

    products = list(qs)
    if comm_status != "ALL":
        products = [
            p for p in products
            if hasattr(p, "commission") and p.commission.status == comm_status
        ]

    return render(request, "producttest/partials/supervisor_rows.html", {
        "products": products,
    })


@system_required("producttest")
@user_passes_test(is_supervisor)
@require_http_methods(["GET", "POST"])
def supervisor_manage(request, pk):
    product = get_object_or_404(TestProduct, pk=pk)
    performance, _ = Performance.objects.get_or_create(product=product)
    commission, _ = Commission.objects.get_or_create(product=product)

    if request.method == "POST":
        perf_form = PerformanceForm(request.POST, instance=performance)
        comm_form = CommissionForm(request.POST, instance=commission)

        if perf_form.is_valid() and comm_form.is_valid():
            with transaction.atomic():
                perf_form.save()
                comm = comm_form.save(commit=False)
                comm.recalculate_per_person()
                comm.save()

                # Update product's manual status if set
                new_status = request.POST.get("manual_status", "").strip()
                if new_status in dict(TestProduct.MANUAL_STATUS_CHOICES):
                    product.manual_status = new_status
                    product.save(update_fields=["manual_status"])

                # Auto-adjust commission status based on test result
                fail_statuses = {TestProduct.STATUS_FAIL, TestProduct.STATUS_CANCEL}
                if product.manual_status in fail_statuses:
                    comm.status = Commission.STATUS_FAILED
                    comm.total = 0
                    comm.per_person = 0
                    comm.save()
                elif comm.status == Commission.STATUS_FAILED:
                    comm.status = Commission.STATUS_WAIT_FILL
                    comm.save()

                # Handle slip uploads
                if comm.status == Commission.STATUS_PAID:
                    files = request.FILES.getlist("slips")
                    if files:
                        commission.slips.all().delete()
                        for f in files:
                            CommissionSlip.objects.create(commission=commission, image=f)

            if request.htmx:
                return HttpResponse(
                    '<script>htmx.trigger("#supervisor-table", "refresh")</script>'
                    '<div class="toast-trigger" data-message="บันทึกผลการดำเนินการสำเร็จ"></div>'
                )
            return redirect("supervisor")
    else:
        perf_form = PerformanceForm(instance=performance)
        comm_form = CommissionForm(instance=commission)

    return render(request, "producttest/partials/supervisor_manage_modal.html", {
        "product": product,
        "perf_form": perf_form,
        "comm_form": comm_form,
        "performance": performance,
        "commission": commission,
        "slips": list(commission.slips.all()),
        "manual_status_choices": TestProduct.MANUAL_STATUS_CHOICES,
    })


# ── Personal Report ───────────────────────────────────────────────────────────

def _current_employee(user):
    """Return the Employee linked to this user, or None."""
    try:
        return user.employee
    except Employee.DoesNotExist:
        return None


@system_required("producttest")
def personal_report(request):
    employee = _current_employee(request.user)
    date_form = DateRangeForm(request.GET or None)

    context = {
        "employee": employee,
        "date_form": date_form,
        "current_status": request.GET.get("status", "ALL"),
        "is_supervisor": is_supervisor(request.user),
    }
    return render(request, "producttest/report.html", context)


@system_required("producttest")
def report_table_partial(request):
    from django.db.models import Q

    employee = _current_employee(request.user)
    if not employee:
        return render(request, "producttest/partials/report_rows.html", {
            "products": [], "all_list": [],
            "stats": {"total": 0, "passed": 0, "failed": 0, "wait_comm": 0,
                      "total_earned": 0, "pass_pct": 0, "fail_pct": 0},
            "no_profile": True,
        })

    emp_name = employee.name
    status_filter = request.GET.get("status", "ALL")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    qs = TestProduct.objects.prefetch_related(
        "graphic_members", "mkt_members", "prices", "pages"
    ).select_related("performance", "commission").filter(
        Q(graphic_members__name=emp_name) | Q(mkt_members__name=emp_name)
    ).distinct()

    if date_from:
        d = parse_date(date_from)
        if d:
            qs = qs.filter(upload_date__gte=d)
    if date_to:
        d = parse_date(date_to)
        if d:
            qs = qs.filter(upload_date__lte=d)

    products = list(qs)

    if status_filter == "ทดสอบผ่าน":
        products = [p for p in products if p.computed_status() == "Test ผ่าน"]
    elif status_filter == "ทดสอบไม่ผ่าน":
        products = [p for p in products if p.computed_status() == "Test ไม่ผ่าน"]
    elif status_filter == "สถานะรอกรอกค่าคอม":
        products = [p for p in products if hasattr(p, "commission") and p.commission.status == Commission.STATUS_WAIT_FILL]

    all_list = list(qs)
    passed = sum(1 for p in all_list if p.computed_status() == "Test ผ่าน")
    failed = sum(1 for p in all_list if p.computed_status() == "Test ไม่ผ่าน")
    wait_comm = sum(1 for p in all_list if hasattr(p, "commission") and p.commission.status == Commission.STATUS_WAIT_FILL)
    total_earned = sum(
        p.commission.per_person
        for p in all_list
        if hasattr(p, "commission") and p.commission.status == Commission.STATUS_PAID
    )

    return render(request, "producttest/partials/report_rows.html", {
        "products": products,
        "all_list": all_list,
        "stats": {
            "total": len(all_list),
            "passed": passed,
            "failed": failed,
            "wait_comm": wait_comm,
            "total_earned": total_earned,
            "pass_pct": round(passed / len(all_list) * 100) if all_list else 0,
            "fail_pct": round(failed / len(all_list) * 100) if all_list else 0,
        },
    })
