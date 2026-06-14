"""
UAT: Phase 3 — Graphic Queue System
Test IDs: GQ-01 … GQ-30
"""
import tempfile
from datetime import date

from django.test import TestCase, Client, override_settings
from django.core.management import call_command

from apps.core.test_utils import make_user, make_image
from apps.producttest.models import Employee
from apps.graphicqueue.models import GraphicJob, MediaType, RefImage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_graphic_employee(name="บอส"):
    return Employee.objects.get_or_create(
        name=name, defaults={"is_graphic": True, "is_active": True}
    )[0]


def make_media_type(name="Test Clip", category=MediaType.CATEGORY_VIDEO):
    return MediaType.objects.get_or_create(name=name, defaults={"category": category})[0]


def make_job(sku="G001", name="Job One", status=GraphicJob.STATUS_WAIT,
             urgency=GraphicJob.URGENCY_NORMAL, product_type=GraphicJob.PRODUCT_TYPE_TEST,
             assignee=None, order_date=None, deadline=None, submit_date=None):
    return GraphicJob.objects.create(
        sku=sku,
        name=name,
        status=status,
        urgency=urgency,
        product_type=product_type,
        assignee=assignee,
        order_date=order_date or date(2025, 6, 1),
        deadline=deadline or date(2025, 6, 10),
        submit_date=submit_date,
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class GQ01_WorkDaysTests(TestCase):
    """work_days property."""

    def test_work_days_calculated_correctly(self):
        """GQ-01 order_date=Jun1, submit_date=Jun6 → 5 days"""
        j = make_job("GQ01", order_date=date(2025, 6, 1), submit_date=date(2025, 6, 6))
        self.assertEqual(j.work_days, 5)

    def test_work_days_min_1(self):
        """GQ-02 same-day submit → work_days = 1 (not 0)"""
        j = make_job("GQ02", order_date=date(2025, 6, 1), submit_date=date(2025, 6, 1))
        self.assertEqual(j.work_days, 1)

    def test_work_days_none_without_submit(self):
        """GQ-03 No submit_date → work_days = None"""
        j = make_job("GQ03")
        self.assertIsNone(j.work_days)


class GQ04_StatusStyleTests(TestCase):
    """status_bg_style and urgency_style properties."""

    def test_status_bg_wait(self):
        """GQ-04 STATUS_WAIT → status_bg_style contains slate (#475569)"""
        j = make_job("GQ04", status=GraphicJob.STATUS_WAIT)
        self.assertIn("#475569", j.status_bg_style)

    def test_status_bg_done(self):
        """GQ-05 STATUS_DONE → status_bg_style contains emerald (#065f46)"""
        j = make_job("GQ05", status=GraphicJob.STATUS_DONE)
        self.assertIn("#065f46", j.status_bg_style)

    def test_urgency_style_urgent(self):
        """GQ-06 URGENCY_URGENT → urgency_style contains #e11d48"""
        j = make_job("GQ06", urgency=GraphicJob.URGENCY_URGENT)
        self.assertIn("#e11d48", j.urgency_style)

    def test_urgency_style_normal(self):
        """GQ-07 URGENCY_NORMAL → urgency_style does not contain red"""
        j = make_job("GQ07", urgency=GraphicJob.URGENCY_NORMAL)
        self.assertNotIn("#e11d48", j.urgency_style)


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------

class GQ_ViewBase(TestCase):
    def setUp(self):
        self.user = make_user("gq_user", groups=["access_graphicqueue"])
        self.c = Client()
        self.c.login(username="gq_user", password="testpass123")


class GQ08_QueueListViewTests(GQ_ViewBase):
    """queue_list view and stat cards."""

    def test_queue_list_200(self):
        """GQ-08 /graphicqueue/ returns 200"""
        r = self.c.get("/graphicqueue/")
        self.assertEqual(r.status_code, 200)

    def test_stat_cards_present(self):
        """GQ-09 stat_cards in context"""
        r = self.c.get("/graphicqueue/")
        self.assertIn("stat_cards", r.context)

    def test_backlog_stat_card_counts_wait_and_progress(self):
        """GQ-10 'งานที่ค้าง' stat = wait + in_progress (not done)"""
        make_job("SG01", status=GraphicJob.STATUS_WAIT)
        make_job("SG02", status=GraphicJob.STATUS_IN_PROGRESS)
        make_job("SG03", status=GraphicJob.STATUS_DONE)
        r = self.c.get("/graphicqueue/")
        # Find the "งานที่ค้าง" card
        cards = r.context["stat_cards"]
        backlog_card = next((c for c in cards if c[0] == "งานที่ค้าง"), None)
        self.assertIsNotNone(backlog_card)
        self.assertEqual(backlog_card[4], 2)  # wait(1) + prog(1) = 2


class GQ11_QueueTablePartialTests(GQ_ViewBase):
    """queue_table_partial HTMX rows and filters."""

    def setUp(self):
        super().setUp()
        self.emp = make_graphic_employee("มอส")
        self.j1 = make_job("GQT01", status=GraphicJob.STATUS_WAIT,
                           product_type=GraphicJob.PRODUCT_TYPE_TEST, assignee=self.emp,
                           order_date=date(2025, 6, 1))
        self.j2 = make_job("GQT02", status=GraphicJob.STATUS_DONE,
                           product_type=GraphicJob.PRODUCT_TYPE_OLD,
                           order_date=date(2025, 7, 1))

    def test_partial_200(self):
        """GQ-11 /graphicqueue/htmx/rows/ returns 200"""
        r = self.c.get("/graphicqueue/htmx/rows/")
        self.assertEqual(r.status_code, 200)

    def test_status_filter_wait(self):
        """GQ-12 ?status=รอดำเนินการ returns only waiting jobs"""
        r = self.c.get("/graphicqueue/htmx/rows/?status=รอดำเนินการ")
        skus = [j.sku for j in r.context["jobs"]]
        self.assertIn("GQT01", skus)
        self.assertNotIn("GQT02", skus)

    def test_backlog_filter_excludes_done(self):
        """GQ-13 ?status=งานที่ค้าง excludes done jobs"""
        r = self.c.get("/graphicqueue/htmx/rows/?status=งานที่ค้าง")
        skus = [j.sku for j in r.context["jobs"]]
        self.assertNotIn("GQT02", skus)
        self.assertIn("GQT01", skus)

    def test_product_type_filter(self):
        """GQ-14 ?product_type=สินค้าเทส returns only test-type jobs"""
        r = self.c.get("/graphicqueue/htmx/rows/?product_type=สินค้าเทส")
        skus = [j.sku for j in r.context["jobs"]]
        self.assertIn("GQT01", skus)
        self.assertNotIn("GQT02", skus)

    def test_assignee_filter(self):
        """GQ-15 ?assignee=มอส returns only jobs for that assignee"""
        r = self.c.get("/graphicqueue/htmx/rows/?assignee=มอส")
        skus = [j.sku for j in r.context["jobs"]]
        self.assertIn("GQT01", skus)
        self.assertNotIn("GQT02", skus)

    def test_month_filter(self):
        """GQ-16 ?month=2025-06 returns only June orders"""
        r = self.c.get("/graphicqueue/htmx/rows/?month=2025-06")
        skus = [j.sku for j in r.context["jobs"]]
        self.assertIn("GQT01", skus)
        self.assertNotIn("GQT02", skus)

    def test_search_filter(self):
        """GQ-17 ?q=GQT02 returns only GQT02"""
        r = self.c.get("/graphicqueue/htmx/rows/?q=GQT02")
        skus = [j.sku for j in r.context["jobs"]]
        self.assertIn("GQT02", skus)
        self.assertNotIn("GQT01", skus)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class GQ18_QueueFormViewTests(GQ_ViewBase):
    """queue_add / queue_edit / queue_delete views."""

    def setUp(self):
        super().setUp()
        self.emp = make_graphic_employee("เบ้น")
        self.mt_video = make_media_type("คลิป 1:1", MediaType.CATEGORY_VIDEO)
        self.mt_image = make_media_type("ภาพ อัลบั้ม", MediaType.CATEGORY_IMAGE)

    def test_queue_add_get_200(self):
        """GQ-18 GET /graphicqueue/add/ returns 200"""
        r = self.c.get("/graphicqueue/add/")
        self.assertEqual(r.status_code, 200)

    def test_queue_add_post_creates_job_with_media(self):
        """GQ-19 POST queue_add creates GraphicJob + media_types M2M"""
        data = {
            "sku": "GQF01",
            "name": "New Job",
            "urgency": GraphicJob.URGENCY_NORMAL,
            "product_type": GraphicJob.PRODUCT_TYPE_TEST,
            "assignee": self.emp.pk,
            "order_date": "2025-06-01",
            "deadline": "2025-06-10",
            "status": GraphicJob.STATUS_WAIT,
            "work_url": "",
            "media_type_ids": [str(self.mt_video.pk), str(self.mt_image.pk)],
        }
        r = self.c.post("/graphicqueue/add/", data)
        self.assertIn(r.status_code, [200, 302])
        self.assertTrue(GraphicJob.objects.filter(sku="GQF01").exists())
        job = GraphicJob.objects.get(sku="GQF01")
        self.assertEqual(job.media_types.count(), 2)

    def test_queue_add_post_creates_ref_images_with_briefs(self):
        """GQ-20 POST queue_add with ref images creates RefImage records with briefs"""
        img1 = make_image("ref1.png")
        img2 = make_image("ref2.png")
        # Files are passed directly in data dict; Django test Client handles multipart automatically
        data = {
            "sku": "GQF02",
            "name": "Ref Job",
            "urgency": GraphicJob.URGENCY_NORMAL,
            "product_type": GraphicJob.PRODUCT_TYPE_TEST,
            "assignee": self.emp.pk,
            "order_date": "2025-06-01",
            "deadline": "2025-06-10",
            "status": GraphicJob.STATUS_WAIT,
            "work_url": "",
            "ref_images": [img1, img2],
            "ref_briefs": ["Brief A", "Brief B"],
        }
        r = self.c.post("/graphicqueue/add/", data)
        self.assertIn(r.status_code, [200, 302])
        self.assertTrue(GraphicJob.objects.filter(sku="GQF02").exists())
        job = GraphicJob.objects.get(sku="GQF02")
        refs = list(job.ref_images.order_by("order"))
        self.assertEqual(len(refs), 2)
        self.assertEqual(refs[0].brief, "Brief A")
        self.assertEqual(refs[1].brief, "Brief B")

    def test_queue_edit_get_200(self):
        """GQ-21 GET queue_edit returns 200"""
        job = make_job("GQF03")
        r = self.c.get(f"/graphicqueue/{job.pk}/edit/")
        self.assertEqual(r.status_code, 200)

    def test_queue_edit_post_updates_job(self):
        """GQ-22 POST queue_edit updates job name and status"""
        job = make_job("GQF04", name="Old Name", status=GraphicJob.STATUS_WAIT)
        data = {
            "sku": "GQF04",
            "name": "New Name",
            "urgency": GraphicJob.URGENCY_NORMAL,
            "product_type": GraphicJob.PRODUCT_TYPE_TEST,
            "assignee": self.emp.pk,
            "order_date": "2025-06-01",
            "deadline": "2025-06-10",
            "status": GraphicJob.STATUS_IN_PROGRESS,
            "work_url": "",
        }
        r = self.c.post(f"/graphicqueue/{job.pk}/edit/", data)
        self.assertIn(r.status_code, [200, 302])
        job.refresh_from_db()
        self.assertEqual(job.name, "New Name")
        self.assertEqual(job.status, GraphicJob.STATUS_IN_PROGRESS)

    def test_queue_edit_deletes_ref_image_on_request(self):
        """GQ-23 POST queue_edit with delete_ref_ids removes that RefImage"""
        job = make_job("GQF05")
        # Create a ref image (via model directly, no file needed for deletion test)
        img = make_image("del_ref.png")
        from django.core.files.uploadedfile import SimpleUploadedFile
        ref = RefImage.objects.create(job=job, image=img, brief="Delete me", order=0)
        data = {
            "sku": "GQF05",
            "name": "Del Ref Job",
            "urgency": GraphicJob.URGENCY_NORMAL,
            "product_type": GraphicJob.PRODUCT_TYPE_TEST,
            "assignee": self.emp.pk,
            "order_date": "2025-06-01",
            "deadline": "2025-06-10",
            "status": GraphicJob.STATUS_WAIT,
            "work_url": "",
            "delete_ref_ids": [str(ref.pk)],
        }
        r = self.c.post(f"/graphicqueue/{job.pk}/edit/", data)
        self.assertIn(r.status_code, [200, 302])
        self.assertFalse(RefImage.objects.filter(pk=ref.pk).exists())

    def test_queue_delete_removes_job(self):
        """GQ-24 POST queue_delete removes the job"""
        job = make_job("GQF06")
        r = self.c.post(f"/graphicqueue/{job.pk}/delete/")
        self.assertIn(r.status_code, [200, 302])
        self.assertFalse(GraphicJob.objects.filter(sku="GQF06").exists())


class GQ25_MediaTypeTests(GQ_ViewBase):
    """media_type_add endpoint: creates new type, preserves checked IDs."""

    def test_media_type_add_creates_new_type(self):
        """GQ-25 POST media_type_add with new name creates MediaType in DB"""
        data = {
            "new_type_name": "New Video Type",
            "new_type_category": MediaType.CATEGORY_VIDEO,
        }
        r = self.c.post("/graphicqueue/htmx/media-type-add/", data)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(MediaType.objects.filter(name="New Video Type").exists())

    def test_media_type_add_new_type_appears_in_response_checked(self):
        """GQ-26 New type appears checked in returned partial"""
        data = {
            "new_type_name": "Autocheck Type",
            "new_type_category": MediaType.CATEGORY_VIDEO,
        }
        r = self.c.post("/graphicqueue/htmx/media-type-add/", data)
        mt = MediaType.objects.get(name="Autocheck Type")
        # The HTML response should have the new type's checkbox checked
        self.assertContains(r, f'value="{mt.pk}"')
        self.assertContains(r, "checked")

    def test_media_type_add_duplicate_does_not_create_new(self):
        """GQ-27 Duplicate name → get_or_create, still only 1 record"""
        make_media_type("Dup Type")
        data = {
            "new_type_name": "Dup Type",
            "new_type_category": MediaType.CATEGORY_VIDEO,
        }
        r = self.c.post("/graphicqueue/htmx/media-type-add/", data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(MediaType.objects.filter(name="Dup Type").count(), 1)

    def test_media_type_add_preserves_checked_ids(self):
        """GQ-28 Existing checked IDs are preserved in the response"""
        mt_existing = make_media_type("Existing Type")
        data = {
            "new_type_name": "Brand New",
            "new_type_category": MediaType.CATEGORY_VIDEO,
            "media_type_ids": [str(mt_existing.pk)],
        }
        r = self.c.post("/graphicqueue/htmx/media-type-add/", data)
        self.assertContains(r, f'value="{mt_existing.pk}"')


class GQ29_ViewModalTests(GQ_ViewBase):
    """view_media_modal and view_ref_modal."""

    def test_view_media_modal_200(self):
        """GQ-29 GET /graphicqueue/<pk>/media/ returns 200"""
        job = make_job("GQM01")
        mt = make_media_type("Clip 1:1", MediaType.CATEGORY_VIDEO)
        job.media_types.add(mt)
        r = self.c.get(f"/graphicqueue/{job.pk}/media/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("video_media", r.context)
        self.assertEqual(len(r.context["video_media"]), 1)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_view_ref_modal_200(self):
        """GQ-30 GET /graphicqueue/<pk>/ref/ returns 200 with refs"""
        job = make_job("GQM02")
        img = make_image("ref_modal.png")
        RefImage.objects.create(job=job, image=img, brief="Test brief", order=0)
        r = self.c.get(f"/graphicqueue/{job.pk}/ref/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["refs"]), 1)
        self.assertEqual(r.context["refs"][0].brief, "Test brief")


class GQ31_SeedGraphicQueueTests(TestCase):
    """seed_graphicqueue management command."""

    def test_seed_creates_10_media_types(self):
        """GQ-31 seed_graphicqueue creates exactly 10 media types (5 video + 5 image)"""
        call_command("seed_graphicqueue", verbosity=0)
        total = MediaType.objects.count()
        self.assertEqual(total, 10)
        video = MediaType.objects.filter(category=MediaType.CATEGORY_VIDEO).count()
        image = MediaType.objects.filter(category=MediaType.CATEGORY_IMAGE).count()
        self.assertEqual(video, 5)
        self.assertEqual(image, 5)

    def test_seed_is_idempotent(self):
        """GQ-32 Running seed_graphicqueue twice does not duplicate types"""
        call_command("seed_graphicqueue", verbosity=0)
        call_command("seed_graphicqueue", verbosity=0)
        self.assertEqual(MediaType.objects.count(), 10)


class GQ33_FormAssigneeQuerysetTests(TestCase):
    """GraphicJobForm assignee queryset is limited to graphic+active employees."""

    def test_form_assignee_limited_to_graphic_active(self):
        """GQ-33 GraphicJobForm.assignee only shows is_graphic=True, is_active=True"""
        Employee.objects.create(name="NonGraphic", is_graphic=False, is_active=True)
        Employee.objects.create(name="InactiveGraphic", is_graphic=True, is_active=False)
        emp_ok = Employee.objects.create(name="ActiveGraphic", is_graphic=True, is_active=True)
        from apps.graphicqueue.forms import GraphicJobForm
        form = GraphicJobForm()
        qs = form.fields["assignee"].queryset
        names = list(qs.values_list("name", flat=True))
        self.assertIn("ActiveGraphic", names)
        self.assertNotIn("NonGraphic", names)
        self.assertNotIn("InactiveGraphic", names)
