"""
UAT: Phase 1 — Product Test System
Test IDs: PT-01 … PT-30
"""
import json
import tempfile
from decimal import Decimal
from datetime import date

from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import Group

from apps.core.test_utils import make_user, make_image
from apps.producttest.models import (
    Employee, TestProduct, TestPrice, ProductPage,
    Performance, Commission, CommissionSlip,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_employee(name="Alice", is_graphic=False, is_mkt=False, is_active=True):
    return Employee.objects.create(name=name, is_graphic=is_graphic,
                                   is_mkt=is_mkt, is_active=is_active)


def make_product(pid="P001", name="Test Product", graphic_members=(), mkt_members=(),
                 manual_status="", upload_date=None, start_date=None, end_date=None):
    p = TestProduct.objects.create(
        pid=pid,
        name=name,
        manual_status=manual_status,
        upload_date=upload_date or date(2025, 1, 1),
        start_date=start_date or date(2025, 1, 2),
        end_date=end_date,
    )
    for emp in graphic_members:
        p.graphic_members.add(emp)
    for emp in mkt_members:
        p.mkt_members.add(emp)
    return p


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class PT01_ComputedStatusTests(TestCase):
    """computed_status() logic matches the mockup spec."""

    def setUp(self):
        self.emp = make_employee("บอส", is_graphic=True, is_mkt=False)

    def test_no_members_auto_wait(self):
        """PT-01 No members, manual=auto → รอดำเนินการ"""
        p = make_product("P001")
        self.assertEqual(p.computed_status(), "รอดำเนินการ")

    def test_graphic_member_auto_progress(self):
        """PT-02 Graphic member assigned, manual=auto → กำลังดำเนินการ"""
        p = make_product("P002", graphic_members=[self.emp])
        self.assertEqual(p.computed_status(), "กำลังดำเนินการ")

    def test_manual_in_progress_wins_over_no_members(self):
        """PT-03 manual=กำลังดำเนินการ, no members → กำลังดำเนินการ"""
        p = make_product("P003", manual_status=TestProduct.STATUS_IN_PROGRESS)
        self.assertEqual(p.computed_status(), "กำลังดำเนินการ")

    def test_manual_pass_wins(self):
        """PT-04 manual=Test ผ่าน → Test ผ่าน regardless of members"""
        p = make_product("P004", manual_status=TestProduct.STATUS_PASS,
                         graphic_members=[self.emp])
        self.assertEqual(p.computed_status(), "Test ผ่าน")

    def test_manual_fail_wins(self):
        """PT-05 manual=Test ไม่ผ่าน → Test ไม่ผ่าน"""
        p = make_product("P005", manual_status=TestProduct.STATUS_FAIL)
        self.assertEqual(p.computed_status(), "Test ไม่ผ่าน")

    def test_manual_cancel_wins(self):
        """PT-06 manual=ยกเลิก → ยกเลิก"""
        p = make_product("P006", manual_status=TestProduct.STATUS_CANCEL)
        self.assertEqual(p.computed_status(), "ยกเลิก")


class PT07_TestDaysTests(TestCase):
    """test_days() property."""

    def test_days_calculated_from_start_to_end(self):
        """PT-07 start=Jan 1, end=Jan 11 → 10 days"""
        p = make_product("P007", start_date=date(2025, 1, 1), end_date=date(2025, 1, 11))
        self.assertEqual(p.test_days(), 10)

    def test_same_day_returns_1(self):
        """PT-08 start == end → 1 (min)"""
        p = make_product("P008", start_date=date(2025, 1, 5), end_date=date(2025, 1, 5))
        self.assertEqual(p.test_days(), 1)

    def test_no_end_date_returns_none(self):
        """PT-09 No end_date → None"""
        p = make_product("P009")
        self.assertIsNone(p.test_days())


class PT10_MemberCountTests(TestCase):
    """member_count() sums graphic + mkt."""

    def test_member_count_combined(self):
        """PT-10 2 graphic + 1 mkt → member_count = 3"""
        g1 = make_employee("G1", is_graphic=True)
        g2 = make_employee("G2", is_graphic=True)
        m1 = make_employee("M1", is_mkt=True)
        p = make_product("P010", graphic_members=[g1, g2], mkt_members=[m1])
        self.assertEqual(p.member_count(), 3)

    def test_member_count_zero(self):
        """PT-11 No members → 0"""
        p = make_product("P011")
        self.assertEqual(p.member_count(), 0)


class PT12_CommissionAutoSplitTests(TestCase):
    """Commission.save() auto-splits total by member count."""

    def test_commission_splits_correctly(self):
        """PT-12 total=3000, 3 members → per_person=1000"""
        g1 = make_employee("G3", is_graphic=True)
        g2 = make_employee("G4", is_graphic=True)
        m1 = make_employee("M2", is_mkt=True)
        p = make_product("P012", graphic_members=[g1, g2], mkt_members=[m1])
        perf, _ = Performance.objects.get_or_create(product=p)
        comm, _ = Commission.objects.get_or_create(product=p)
        comm.total = Decimal("3000")
        comm.save()
        comm.refresh_from_db()
        self.assertEqual(comm.per_person, Decimal("1000.00"))

    def test_commission_zero_members_gives_zero(self):
        """PT-13 total=5000, 0 members → per_person=0"""
        p = make_product("P013")
        perf, _ = Performance.objects.get_or_create(product=p)
        comm, _ = Commission.objects.get_or_create(product=p)
        comm.total = Decimal("5000")
        comm.save()
        comm.refresh_from_db()
        self.assertEqual(comm.per_person, Decimal("0"))


class PT14_PerformancePropertyTests(TestCase):
    """Performance computed properties."""

    def setUp(self):
        p = make_product("P014")
        self.perf, _ = Performance.objects.get_or_create(product=p)

    def test_profit_is_negative_true(self):
        """PT-14 Negative profit → profit_is_negative True"""
        self.perf.profit = Decimal("-100")
        self.perf.save()
        self.assertTrue(self.perf.profit_is_negative)

    def test_profit_is_negative_false(self):
        """PT-15 Positive profit → profit_is_negative False"""
        self.perf.profit = Decimal("100")
        self.perf.save()
        self.assertFalse(self.perf.profit_is_negative)

    def test_ads_pct_calculation(self):
        """PT-16 ads=500, sales=2000 → ads_pct=25.0"""
        self.perf.ads = Decimal("500")
        self.perf.sales = Decimal("2000")
        self.perf.save()
        self.assertEqual(self.perf.ads_pct, 25.0)

    def test_ads_pct_zero_sales_returns_zero(self):
        """PT-17 sales=0 → ads_pct=0 (no ZeroDivisionError)"""
        self.perf.ads = Decimal("500")
        self.perf.sales = Decimal("0")
        self.perf.save()
        self.assertEqual(self.perf.ads_pct, 0.0)

    def test_profit_pct_calculation(self):
        """PT-18 profit=400, sales=2000 → profit_pct=20.0"""
        self.perf.profit = Decimal("400")
        self.perf.sales = Decimal("2000")
        self.perf.save()
        self.assertEqual(self.perf.profit_pct, 20.0)


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------

class PT_ViewBase(TestCase):
    """Base class: pt_user with access_producttest; supervisor has both groups."""

    def setUp(self):
        self.pt_user = make_user("pt_view_user", groups=["access_producttest"])
        self.supervisor = make_user(
            "pt_supervisor", groups=["access_producttest", "supervisor"]
        )
        self.c = Client()
        self.c.login(username="pt_view_user", password="testpass123")
        self.sc = Client()
        self.sc.login(username="pt_supervisor", password="testpass123")


class PT19_ProductListViewTests(PT_ViewBase):
    """product_list view."""

    def test_product_list_200(self):
        """PT-19 /producttest/ returns 200"""
        r = self.c.get("/producttest/")
        self.assertEqual(r.status_code, 200)

    def test_stat_cards_present_in_context(self):
        """PT-20 stat_cards in context"""
        r = self.c.get("/producttest/")
        self.assertIn("stat_cards", r.context)


class PT21_ProductTablePartialTests(PT_ViewBase):
    """product_table_partial HTMX view."""

    def setUp(self):
        super().setUp()
        emp = make_employee("ฟาง", is_mkt=True)
        self.p1 = make_product("PA01", name="Alpha", mkt_members=[emp])
        self.p2 = make_product("PA02", name="Beta")

    def test_partial_200(self):
        """PT-21 /producttest/htmx/products/ returns 200"""
        r = self.c.get("/producttest/htmx/products/")
        self.assertEqual(r.status_code, 200)

    def test_search_filter(self):
        """PT-22 ?q=Alpha returns only Alpha in context"""
        r = self.c.get("/producttest/htmx/products/?q=Alpha")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["products"]), 1)
        self.assertEqual(r.context["products"][0].name, "Alpha")

    def test_status_filter_wait(self):
        """PT-23 ?status=รอดำเนินการ returns only PA02 (no members)"""
        r = self.c.get("/producttest/htmx/products/?status=รอดำเนินการ")
        pids = [p.pid for p in r.context["products"]]
        self.assertIn("PA02", pids)
        self.assertNotIn("PA01", pids)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PT24_ProductFormTests(PT_ViewBase):
    """product_add / product_edit / product_delete views."""

    def test_product_add_get_200(self):
        """PT-24 GET /producttest/products/add/ returns 200"""
        r = self.c.get("/producttest/products/add/")
        self.assertEqual(r.status_code, 200)

    def test_product_add_post_creates_product(self):
        """PT-25 POST product add creates TestProduct + Performance + Commission"""
        data = {
            "pid": "PX01",
            "name": "New Product",
            "upload_date": "2025-06-01",
            "start_date": "2025-06-02",
            "manual_status": "",
            "prices_json": '["100","200"]',
            "pages_json": '[{"page":"Shopee","url":"http://shopee.th"}]',
        }
        r = self.c.post("/producttest/products/add/", data)
        self.assertIn(r.status_code, [200, 302])
        self.assertTrue(TestProduct.objects.filter(pid="PX01").exists())
        p = TestProduct.objects.get(pid="PX01")
        self.assertTrue(Performance.objects.filter(product=p).exists())
        self.assertTrue(Commission.objects.filter(product=p).exists())
        self.assertEqual(p.prices.count(), 2)
        self.assertEqual(p.pages.count(), 1)

    def test_product_add_skips_blank_price(self):
        """PT-26 prices_json with blank entry → blank skipped"""
        data = {
            "pid": "PX02",
            "name": "Blank Price Test",
            "upload_date": "2025-06-01",
            "start_date": "2025-06-02",
            "manual_status": "",
            "prices_json": '["200",""]',
            "pages_json": "[]",
        }
        self.c.post("/producttest/products/add/", data)
        p = TestProduct.objects.get(pid="PX02")
        self.assertEqual(p.prices.count(), 1)

    def test_product_edit_updates_name(self):
        """PT-27 POST product_edit updates name"""
        emp = make_employee("EditEmp", is_graphic=True)
        p = make_product("PX03", name="Before")
        Performance.objects.get_or_create(product=p)
        Commission.objects.get_or_create(product=p)
        data = {
            "pid": "PX03",
            "name": "After",
            "upload_date": "2025-06-01",
            "start_date": "2025-06-02",
            "manual_status": "",
            "prices_json": "[]",
            "pages_json": "[]",
        }
        r = self.c.post(f"/producttest/products/{p.pk}/edit/", data)
        self.assertIn(r.status_code, [200, 302])
        p.refresh_from_db()
        self.assertEqual(p.name, "After")

    def test_product_delete(self):
        """PT-28 POST product_delete removes the product"""
        p = make_product("PX04")
        r = self.c.post(f"/producttest/products/{p.pk}/delete/")
        self.assertIn(r.status_code, [200, 302])
        self.assertFalse(TestProduct.objects.filter(pid="PX04").exists())


class PT29_SupervisorGatingTests(PT_ViewBase):
    """Supervisor-only views are gated correctly."""

    def test_non_supervisor_to_supervisor_view_is_redirected(self):
        """PT-29 access_producttest-only user → /producttest/supervisor/ is redirected (user_passes_test)"""
        r = self.c.get("/producttest/supervisor/")
        self.assertEqual(r.status_code, 302)

    def test_supervisor_can_access_supervisor_view(self):
        """PT-30 supervisor user → /producttest/supervisor/ 200"""
        r = self.sc.get("/producttest/supervisor/")
        self.assertEqual(r.status_code, 200)


class PT31_ReportLockedToCurrentUser(PT_ViewBase):
    """Personal report shows current user's data, no employee selector."""

    def test_report_200_without_employee_profile(self):
        """PT-31 Report page loads even when user has no Employee profile linked"""
        r = self.c.get("/producttest/report/")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context["employee"])

    def test_report_shows_linked_employee(self):
        """PT-32 Report page shows the Employee linked to request.user"""
        emp = make_employee("ReportEmp", is_graphic=True)
        emp.user = self.pt_user
        emp.save()
        r = self.c.get("/producttest/report/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["employee"].name, "ReportEmp")

    def test_report_partial_no_profile_returns_no_profile_flag(self):
        """PT-33 report_table_partial returns no_profile=True when user has no Employee"""
        r = self.c.get("/producttest/htmx/report/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["no_profile"])

    def test_employee_nickname_field_exists(self):
        """PT-34 Employee.nickname field is present"""
        emp = make_employee("NickEmp")
        emp.nickname = "เล็ก"
        emp.save()
        emp.refresh_from_db()
        self.assertEqual(emp.nickname, "เล็ก")
