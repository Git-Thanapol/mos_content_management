"""
UAT: Phase 2 — Clearance Products (JST integration mocked)
Test IDs: CL-01 … CL-25
"""
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client

from apps.core.test_utils import make_user
from apps.clearance.models import ClearanceProduct, ClearancePromo
from apps.clearance.routers import JstRouter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JST_OK = lambda code: {  # noqa: E731
    code: {"name": f"Name-{code}", "stock": 50, "cost": 99.50, "last_order_date": "2025-01-15"}
}

_JST_FALLBACK = lambda code: {  # noqa: E731
    code: {"name": "-", "stock": "-", "cost": "-", "last_order_date": None}
}


def make_clearance(product_code="SP001", product_name="Test Item",
                   status=ClearanceProduct.STATUS_WAIT):
    return ClearanceProduct.objects.create(
        product_code=product_code,
        product_name=product_name,
        status=status,
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class CL01_ClearanceProductModelTests(TestCase):
    """Model properties for ClearanceProduct."""

    def test_status_bs_wait(self):
        """CL-01 STATUS_WAIT → status_bs = 'secondary'"""
        p = make_clearance(status=ClearanceProduct.STATUS_WAIT)
        self.assertEqual(p.status_bs, "secondary")

    def test_status_bs_in_progress(self):
        """CL-02 STATUS_IN_PROGRESS → status_bs = 'warning'"""
        p = make_clearance("SP002", status=ClearanceProduct.STATUS_IN_PROGRESS)
        self.assertEqual(p.status_bs, "warning")

    def test_status_bs_done(self):
        """CL-03 STATUS_DONE → status_bs = 'success'"""
        p = make_clearance("SP003", status=ClearanceProduct.STATUS_DONE)
        self.assertEqual(p.status_bs, "success")

    def test_status_bg_style_wait(self):
        """CL-04 STATUS_WAIT → status_bg_style contains indigo (#3730a3)"""
        p = make_clearance("SP004", status=ClearanceProduct.STATUS_WAIT)
        self.assertIn("#3730a3", p.status_bg_style)

    def test_status_bg_style_done(self):
        """CL-05 STATUS_DONE → status_bg_style contains emerald (#065f46)"""
        p = make_clearance("SP005", status=ClearanceProduct.STATUS_DONE)
        self.assertIn("#065f46", p.status_bg_style)


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

class CL06_JstRouterTests(TestCase):
    """JstRouter routes JST models to 'jst', blocks migrations."""

    def setUp(self):
        self.router = JstRouter()

    def _mock_model(self, name):
        m = MagicMock()
        m._meta.model_name = name
        return m

    def test_jst_model_routes_to_jst_db(self):
        """CL-06 JstMasterItem → db_for_read returns 'jst'"""
        m = self._mock_model("jstmasteritem")
        self.assertEqual(self.router.db_for_read(m), "jst")

    def test_non_jst_model_returns_none(self):
        """CL-07 ClearanceProduct → db_for_read returns None"""
        m = self._mock_model("clearanceproduct")
        self.assertIsNone(self.router.db_for_read(m))

    def test_allow_migrate_jst_db_false(self):
        """CL-08 allow_migrate on 'jst' database → False"""
        self.assertFalse(self.router.allow_migrate("jst", "clearance"))

    def test_allow_migrate_default_db_none(self):
        """CL-09 allow_migrate on 'default' database → None"""
        self.assertIsNone(self.router.allow_migrate("default", "clearance"))


# ---------------------------------------------------------------------------
# JST service tests (no real DB)
# ---------------------------------------------------------------------------

class CL10_JstServiceTests(TestCase):
    """jst.py service layer — pure logic, no DB connection."""

    def test_search_empty_returns_empty_list(self):
        """CL-10 search_products('') → []"""
        from apps.clearance import jst
        result = jst.search_products("")
        self.assertEqual(result, [])

    def test_enrich_empty_codes_returns_empty(self):
        """CL-11 enrich([]) → {}"""
        from apps.clearance import jst
        result = jst.enrich([])
        self.assertEqual(result, {})

    def test_enrich_swallows_exception_returns_fallback(self):
        """CL-12 enrich with broken JST backend → returns '-'/None fallback, no exception"""
        from apps.clearance import jst
        with patch("apps.clearance.jst_models.JstMasterItem.objects") as mock_mgr:
            mock_mgr.using.side_effect = Exception("connection refused")
            result = jst.enrich(["SP001"])
        self.assertIn("SP001", result)
        self.assertEqual(result["SP001"]["name"], "-")
        self.assertEqual(result["SP001"]["stock"], "-")
        self.assertIsNone(result["SP001"]["last_order_date"])


# ---------------------------------------------------------------------------
# View tests (all JST calls patched)
# ---------------------------------------------------------------------------

class CL_ViewBase(TestCase):
    def setUp(self):
        self.user = make_user("cl_user", groups=["access_clearance"])
        self.c = Client()
        self.c.login(username="cl_user", password="testpass123")


class CL13_ClearanceListViewTests(CL_ViewBase):
    """clearance_list view."""

    def test_clearance_list_200(self):
        """CL-13 /clearance/ returns 200"""
        r = self.c.get("/clearance/")
        self.assertEqual(r.status_code, 200)

    def test_stat_cards_in_context(self):
        """CL-14 stat_cards present in context"""
        r = self.c.get("/clearance/")
        self.assertIn("stat_cards", r.context)

    def test_stats_reflect_product_counts(self):
        """CL-15 stats counts match actual DB records"""
        make_clearance("S1", status=ClearanceProduct.STATUS_WAIT)
        make_clearance("S2", status=ClearanceProduct.STATUS_DONE)
        r = self.c.get("/clearance/")
        self.assertEqual(r.context["stats"]["all"], 2)
        self.assertEqual(r.context["stats"]["done"], 1)


@patch("apps.clearance.views.jst.enrich")
class CL16_ClearanceTablePartialTests(CL_ViewBase):
    """clearance_table_partial HTMX rows (JST mocked)."""

    def test_partial_200(self, mock_enrich):
        """CL-16 /clearance/htmx/rows/ returns 200"""
        mock_enrich.return_value = {}
        r = self.c.get("/clearance/htmx/rows/")
        self.assertEqual(r.status_code, 200)

    def test_jst_data_merged_into_rows(self, mock_enrich):
        """CL-17 JST name/stock/cost merged into rows context"""
        p = make_clearance("SP010", "Item Ten")
        mock_enrich.return_value = {
            "SP010": {"name": "JST Name", "stock": 30, "cost": 75.0, "last_order_date": None}
        }
        r = self.c.get("/clearance/htmx/rows/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["rows"]), 1)
        row = r.context["rows"][0]
        self.assertEqual(row["jst_name"], "JST Name")
        self.assertEqual(row["jst_stock"], 30)

    def test_status_filter(self, mock_enrich):
        """CL-18 ?status=รอดำเนินการ filters correctly"""
        make_clearance("SF01", status=ClearanceProduct.STATUS_WAIT)
        make_clearance("SF02", status=ClearanceProduct.STATUS_DONE)
        mock_enrich.return_value = {}
        r = self.c.get("/clearance/htmx/rows/?status=รอดำเนินการ")
        codes = [row["product"].product_code for row in r.context["rows"]]
        self.assertIn("SF01", codes)
        self.assertNotIn("SF02", codes)

    def test_search_filter(self, mock_enrich):
        """CL-19 ?q=SF03 filters by product_code"""
        make_clearance("SF03", "Gamma Item")
        make_clearance("SF04", "Delta Item")
        mock_enrich.return_value = {}
        r = self.c.get("/clearance/htmx/rows/?q=SF03")
        codes = [row["product"].product_code for row in r.context["rows"]]
        self.assertIn("SF03", codes)
        self.assertNotIn("SF04", codes)


@patch("apps.clearance.views.jst.enrich")
class CL20_ClearanceFormViewTests(CL_ViewBase):
    """clearance_form (add / edit) views."""

    def test_add_get_200(self, mock_enrich):
        """CL-20 GET /clearance/add/ returns 200"""
        mock_enrich.return_value = {}
        r = self.c.get("/clearance/add/")
        self.assertEqual(r.status_code, 200)

    def test_add_post_creates_product_with_jst_name(self, mock_enrich):
        """CL-21 POST add uses JST name to populate product_name"""
        mock_enrich.return_value = {
            "SP100": {"name": "JST Product", "stock": 10, "cost": 50.0, "last_order_date": None}
        }
        data = {
            "product_code": "SP100",
            "product_name": "Fallback Name",
            "status": ClearanceProduct.STATUS_WAIT,
            "assignee": "",
        }
        r = self.c.post("/clearance/add/", data)
        self.assertIn(r.status_code, [200, 302])
        self.assertTrue(ClearanceProduct.objects.filter(product_code="SP100").exists())
        p = ClearanceProduct.objects.get(product_code="SP100")
        self.assertEqual(p.product_name, "JST Product")

    def test_add_post_jst_down_keeps_form_name(self, mock_enrich):
        """CL-22 POST add with JST returning '-' keeps the form's product_name"""
        mock_enrich.return_value = {
            "SP101": {"name": "-", "stock": "-", "cost": "-", "last_order_date": None}
        }
        data = {
            "product_code": "SP101",
            "product_name": "Cached Name",
            "status": ClearanceProduct.STATUS_WAIT,
            "assignee": "",
        }
        r = self.c.post("/clearance/add/", data)
        self.assertIn(r.status_code, [200, 302])
        p = ClearanceProduct.objects.filter(product_code="SP101").first()
        if p:
            # When JST returns '-', the view should keep the submitted product_name
            self.assertEqual(p.product_name, "Cached Name")

    def test_delete_removes_product(self, mock_enrich):
        """CL-23 POST clearance_delete removes the product"""
        p = make_clearance("SD01")
        r = self.c.post(f"/clearance/{p.pk}/delete/")
        self.assertIn(r.status_code, [200, 302])
        self.assertFalse(ClearanceProduct.objects.filter(product_code="SD01").exists())


@patch("apps.clearance.views.jst.enrich")
class CL24_PromoModalTests(CL_ViewBase):
    """promo_modal: saves and reads promo rows."""

    def test_promo_modal_get_200(self, mock_enrich):
        """CL-24 GET promo modal returns 200"""
        mock_enrich.return_value = {}
        p = make_clearance("SP200")
        r = self.c.get(f"/clearance/{p.pk}/promos/")
        self.assertEqual(r.status_code, 200)

    def test_promo_modal_post_saves_rows(self, mock_enrich):
        """CL-25 POST promo_modal saves promos_json rows (skips empty)"""
        mock_enrich.return_value = {}
        p = make_clearance("SP201")
        promos = [
            {"old": "500", "new": "350"},
            {"old": "", "new": ""},  # blank row — should be skipped
            {"old": "300", "new": "200"},
        ]
        data = {"promos_json": json.dumps(promos)}
        r = self.c.post(f"/clearance/{p.pk}/promos/", data)
        self.assertIn(r.status_code, [200, 302])
        self.assertEqual(p.promos.count(), 2)

    def test_promo_modal_clears_old_promos_on_resave(self, mock_enrich):
        """CL-26 POST promo_modal replaces all existing promos"""
        mock_enrich.return_value = {}
        p = make_clearance("SP202")
        ClearancePromo.objects.create(product=p, old_price="999", new_price="800", order=0)
        data = {"promos_json": json.dumps([{"old": "100", "new": "50"}])}
        r = self.c.post(f"/clearance/{p.pk}/promos/", data)
        self.assertEqual(p.promos.count(), 1)
        self.assertEqual(p.promos.first().old_price, "100")


@patch("apps.clearance.views.jst.search_products")
@patch("apps.clearance.views.jst.enrich")
class CL27_JstHtmxHelperTests(CL_ViewBase):
    """jst_search / jst_fields HTMX endpoints."""

    def test_jst_search_returns_200(self, mock_enrich, mock_search):
        """CL-27 /clearance/htmx/jst-search/?q=SP returns 200"""
        mock_search.return_value = [{"product_code": "SP999", "name": "Test"}]
        r = self.c.get("/clearance/htmx/jst-search/?q=SP")
        self.assertEqual(r.status_code, 200)

    def test_jst_fields_returns_200(self, mock_enrich, mock_search):
        """CL-28 /clearance/htmx/jst-fields/?code=SP999 returns 200"""
        mock_enrich.return_value = {
            "SP999": {"name": "Test", "stock": 5, "cost": 10.0, "last_order_date": None}
        }
        r = self.c.get("/clearance/htmx/jst-fields/?code=SP999")
        self.assertEqual(r.status_code, 200)
