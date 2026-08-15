"""
UAT: Phase 4 — Page Manager
Test IDs: PM-01 … PM-20
"""
from datetime import date

from django.core.exceptions import ValidationError
from django.test import Client, TestCase

from apps.core.test_utils import make_user
from apps.pagemanager.models import FacebookPage, PagePost, PageSKU, PostMediaType
from apps.producttest.models import Employee


def make_employee(name, user=None):
    return Employee.objects.get_or_create(name=name, defaults={"is_active": True, "user": user})[0]


def make_page(page_name="Page A", page_id="111111", owners=()):
    page = FacebookPage.objects.create(page_name=page_name, page_id=page_id)
    if owners:
        page.owners.set(owners)
    return page


class PM01_ModelPropertyTests(TestCase):
    """FacebookPage / PagePost link + validator properties."""

    def test_chat_and_page_url(self):
        """PM-01 chat_url / page_url built from page_id"""
        page = make_page(page_id="999888")
        self.assertEqual(page.chat_url, "https://www.facebook.com/latest/inbox/all?asset_id=999888")
        self.assertEqual(page.page_url, "https://www.facebook.com/999888")

    def test_page_id_must_be_numeric(self):
        """PM-02 non-numeric page_id fails validation"""
        page = FacebookPage(page_name="Bad", page_id="abc123")
        with self.assertRaises(ValidationError):
            page.full_clean()

    def test_post_url(self):
        """PM-03 post_url built from post_id"""
        page = make_page()
        post = PagePost.objects.create(page=page, post_id="123456789", post_date=date(2025, 1, 1))
        self.assertEqual(post.post_url, "https://www.facebook.com/123456789")


class PM04_SkuSyncTests(TestCase):
    """Add/edit view syncs PageSKU rows."""

    def setUp(self):
        self.sup = make_user("pm_sup", groups=["access_pagemanager", "supervisor"])
        self.c = Client()
        self.c.login(username="pm_sup", password="testpass123")

    def test_add_page_creates_skus(self):
        """PM-04 POST page_add with sku_code/sku_name creates PageSKU rows in order"""
        data = {
            "page_name": "New Page", "page_id": "222333", "status": FacebookPage.STATUS_NEW,
            "sku_code": ["SP001", "SP002"], "sku_name": ["Product 1", "Product 2"],
        }
        r = self.c.post("/pagemanager/add/", data)
        self.assertIn(r.status_code, [200, 302])
        page = FacebookPage.objects.get(page_id="222333")
        codes = list(page.skus.order_by("order").values_list("product_code", flat=True))
        self.assertEqual(codes, ["SP001", "SP002"])

    def test_edit_page_replaces_skus(self):
        """PM-05 editing a page replaces its SKU set entirely"""
        page = make_page(page_id="333444")
        PageSKU.objects.create(page=page, product_code="OLD001", product_name="Old", order=0)
        data = {
            "page_name": page.page_name, "page_id": page.page_id, "status": FacebookPage.STATUS_NEW,
            "sku_code": ["NEW001"], "sku_name": ["New"],
        }
        r = self.c.post(f"/pagemanager/{page.pk}/edit/", data)
        self.assertIn(r.status_code, [200, 302])
        codes = list(page.skus.values_list("product_code", flat=True))
        self.assertEqual(codes, ["NEW001"])

    def test_sku_filter_returns_matching_page(self):
        """PM-06 ?sku= filters page_table_partial by PageSKU.product_code"""
        page = make_page(page_id="444555")
        PageSKU.objects.create(page=page, product_code="FINDME", order=0)
        make_page(page_name="Other", page_id="555666")
        r = self.c.get("/pagemanager/htmx/rows/?sku=FINDME")
        names = [p.page_name for p in r.context["pages"]]
        self.assertIn(page.page_name, names)
        self.assertEqual(len(names), 1)


class PM07_VisibilityTests(TestCase):
    """Row-level visibility: non-supervisors see only pages they own."""

    def setUp(self):
        self.emp_a = make_employee("Admin A")
        self.emp_b = make_employee("Admin B")
        self.user_a = make_user("pm_a", groups=["access_pagemanager"])
        self.emp_a.user = self.user_a
        self.emp_a.save()
        self.page_a = make_page("Page A", "111000", owners=[self.emp_a])
        self.page_b = make_page("Page B", "222000", owners=[self.emp_b])
        self.c = Client()
        self.c.login(username="pm_a", password="testpass123")

    def test_own_page_visible_in_list(self):
        """PM-07 non-supervisor sees only their own page in page_table_partial"""
        r = self.c.get("/pagemanager/htmx/rows/")
        names = [p.page_name for p in r.context["pages"]]
        self.assertIn("Page A", names)
        self.assertNotIn("Page B", names)

    def test_non_supervisor_does_not_see_edit_button(self):
        """PM-07b non-supervisor's rendered rows never contain the edit/delete icons"""
        r = self.c.get("/pagemanager/htmx/rows/")
        self.assertFalse(r.context["is_supervisor"])
        self.assertNotContains(r, "fa-pen-to-square")
        self.assertNotContains(r, "fa-trash-can")

    def test_other_page_404_on_posts(self):
        """PM-08 opening another admin's page posts URL returns 404"""
        r = self.c.get(f"/pagemanager/{self.page_b.pk}/posts/")
        self.assertEqual(r.status_code, 404)

    def test_other_page_post_add_404(self):
        """PM-09 posting to another admin's page add-post URL returns 404"""
        r = self.c.post(f"/pagemanager/{self.page_b.pk}/posts/add/", {})
        self.assertEqual(r.status_code, 404)

    def test_non_supervisor_cannot_add_page(self):
        """PM-10 non-supervisor is forbidden from page_add"""
        r = self.c.get("/pagemanager/add/")
        self.assertNotEqual(r.status_code, 200)

    def test_non_supervisor_cannot_delete_page(self):
        """PM-11 non-supervisor is forbidden from page_delete"""
        r = self.c.post(f"/pagemanager/{self.page_a.pk}/delete/")
        self.assertNotEqual(r.status_code, 200)
        self.assertTrue(FacebookPage.objects.filter(pk=self.page_a.pk).exists())


class PM12_SupervisorNoteTests(TestCase):
    """supervisor_note must never leak to non-supervisors."""

    def setUp(self):
        self.emp_a = make_employee("Admin A2")
        self.user_a = make_user("pm_a2", groups=["access_pagemanager"])
        self.emp_a.user = self.user_a
        self.emp_a.save()
        self.page = make_page("Page X", "777000", owners=[self.emp_a])
        PagePost.objects.create(
            page=self.page, post_id="1111111", post_date=date(2025, 1, 1),
            note="employee note", supervisor_note="SECRET SUPERVISOR TEXT",
        )
        self.c = Client()
        self.c.login(username="pm_a2", password="testpass123")

    def test_supervisor_note_not_in_post_table_html(self):
        """PM-12 non-supervisor's rendered post table never contains supervisor_note text"""
        r = self.c.get(f"/pagemanager/{self.page.pk}/posts/htmx/rows/")
        self.assertNotContains(r, "SECRET SUPERVISOR TEXT")

    def test_supervisor_note_field_removed_from_form(self):
        """PM-13 non-supervisor's post_form does not include supervisor_note field"""
        r = self.c.get(f"/pagemanager/{self.page.pk}/posts/add/")
        self.assertNotIn("supervisor_note", r.context["form"].fields)

    def test_supervisor_note_not_in_export(self):
        """PM-14 non-supervisor's export_page_posts xlsx omits supervisor_note column"""
        r = self.c.get(f"/pagemanager/{self.page.pk}/export/posts/")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b"SECRET SUPERVISOR TEXT", r.content)

    def test_post_edit_by_non_supervisor_does_not_wipe_supervisor_note(self):
        """PM-15 non-supervisor editing a post (without the field) leaves supervisor_note untouched"""
        post = self.page.posts.first()
        data = {
            "product_code": "", "product_name": "",
            "post_id": post.post_id, "post_date": "2025-01-02", "note": "updated note",
        }
        r = self.c.post(f"/pagemanager/{self.page.pk}/posts/{post.pk}/edit/", data)
        self.assertIn(r.status_code, [200, 302])
        post.refresh_from_db()
        self.assertEqual(post.supervisor_note, "SECRET SUPERVISOR TEXT")
        self.assertEqual(post.note, "updated note")


class PM16_SupervisorSeesAllTests(TestCase):
    """Supervisors see every page and every export column."""

    def setUp(self):
        self.emp_a = make_employee("Admin A3")
        self.emp_b = make_employee("Admin B3")
        make_page("Page A3", "888000", owners=[self.emp_a])
        make_page("Page B3", "999000", owners=[self.emp_b])
        self.sup = make_user("pm_sup2", groups=["access_pagemanager", "supervisor"])
        self.c = Client()
        self.c.login(username="pm_sup2", password="testpass123")

    def test_supervisor_sees_all_pages(self):
        """PM-16 supervisor's page_table_partial includes every page regardless of owner"""
        r = self.c.get("/pagemanager/htmx/rows/")
        names = [p.page_name for p in r.context["pages"]]
        self.assertIn("Page A3", names)
        self.assertIn("Page B3", names)

    def test_supervisor_sees_edit_button_in_rendered_html(self):
        """PM-16b page_table_partial passes is_supervisor so the edit/delete buttons actually render (regression: view once forgot this context key)"""
        r = self.c.get("/pagemanager/htmx/rows/")
        self.assertTrue(r.context["is_supervisor"])
        self.assertContains(r, "fa-pen-to-square")

    def test_supervisor_export_all_posts_200(self):
        """PM-17 export_all_posts returns 200 xlsx for a supervisor"""
        r = self.c.get("/pagemanager/export/posts/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheetml", r["Content-Type"])


class PM18_AccessGateTests(TestCase):
    """system_required gate."""

    def test_no_group_gets_403(self):
        """PM-18 user without access_pagemanager group gets 403"""
        make_user("pm_noaccess")
        c = Client()
        c.login(username="pm_noaccess", password="testpass123")
        r = c.get("/pagemanager/")
        self.assertEqual(r.status_code, 403)

    def test_unauthenticated_redirects_to_login(self):
        """PM-19 unauthenticated request redirects to login"""
        c = Client()
        r = c.get("/pagemanager/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r.url)


class PM20_SeedCommandTests(TestCase):
    """seed_pagemanager management command."""

    def test_seed_creates_6_media_types_idempotently(self):
        """PM-20 seed_pagemanager creates 6 types and is safe to run twice"""
        from django.core.management import call_command
        call_command("seed_pagemanager", verbosity=0)
        call_command("seed_pagemanager", verbosity=0)
        self.assertEqual(PostMediaType.objects.count(), 6)


class PM21_LoginLinkedPickerTests(TestCase):
    """owners / poster pickers are restricted to login-linked employees and labeled by nickname."""

    def setUp(self):
        self.with_login = make_employee("Full Name Only")
        u = make_user("pm_picker_user")
        self.with_login.user = u
        self.with_login.save()
        self.with_nickname = make_employee("Another Full Name")
        self.with_nickname.nickname = "เล็ก"
        u2 = make_user("pm_picker_user2")
        self.with_nickname.user = u2
        self.with_nickname.save()
        self.no_login = make_employee("No Login Employee")

    def test_owners_queryset_excludes_employee_without_login(self):
        """PM-21 FacebookPageForm.owners only offers employees linked to a login account"""
        from apps.pagemanager.forms import FacebookPageForm
        qs = FacebookPageForm().fields["owners"].queryset
        self.assertIn(self.with_login, qs)
        self.assertIn(self.with_nickname, qs)
        self.assertNotIn(self.no_login, qs)

    def test_poster_queryset_excludes_employee_without_login(self):
        """PM-22 PagePostForm.poster only offers employees linked to a login account"""
        from apps.pagemanager.forms import PagePostForm
        qs = PagePostForm().fields["poster"].queryset
        self.assertIn(self.with_login, qs)
        self.assertNotIn(self.no_login, qs)

    def test_owners_label_prefers_nickname(self):
        """PM-23 owners choice label uses nickname when set, falls back to name otherwise"""
        from apps.pagemanager.forms import FacebookPageForm
        field = FacebookPageForm().fields["owners"]
        self.assertEqual(field.label_from_instance(self.with_nickname), "เล็ก")
        self.assertEqual(field.label_from_instance(self.with_login), "Full Name Only")

    def test_poster_label_prefers_nickname(self):
        """PM-24 poster choice label uses nickname when set, falls back to name otherwise"""
        from apps.pagemanager.forms import PagePostForm
        field = PagePostForm().fields["poster"]
        self.assertEqual(field.label_from_instance(self.with_nickname), "เล็ก")
