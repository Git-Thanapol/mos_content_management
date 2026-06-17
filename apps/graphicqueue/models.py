from django.db import models
from apps.producttest.models import Employee


class MediaType(models.Model):
    CATEGORY_VIDEO = "video"
    CATEGORY_IMAGE = "image"
    CATEGORY_CHOICES = [
        (CATEGORY_VIDEO, "งานคลิป"),
        (CATEGORY_IMAGE, "งานรูปภาพ"),
    ]

    name = models.CharField(max_length=200, unique=True, verbose_name="ชื่อประเภทสื่อ")
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default=CATEGORY_VIDEO)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["category", "order", "id"]
        verbose_name = "ประเภทสื่อ"
        verbose_name_plural = "ประเภทสื่อ"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.name}"


class GraphicJob(models.Model):
    STATUS_WAIT = "รอดำเนินการ"
    STATUS_IN_PROGRESS = "กำลังดำเนินการ"
    STATUS_DONE = "เรียบร้อย"
    STATUS_CHOICES = [
        (STATUS_WAIT, "รอดำเนินการ"),
        (STATUS_IN_PROGRESS, "กำลังดำเนินการ"),
        (STATUS_DONE, "เรียบร้อย"),
    ]

    URGENCY_NORMAL = "ทั่วไป"
    URGENCY_URGENT = "ด่วน"
    URGENCY_CHOICES = [
        (URGENCY_NORMAL, "ทั่วไป"),
        (URGENCY_URGENT, "ด่วน"),
    ]

    PRODUCT_TYPE_TEST = "สินค้าเทส"
    PRODUCT_TYPE_OLD = "สินค้าเก่า"
    PRODUCT_TYPE_CHOICES = [
        (PRODUCT_TYPE_TEST, "สินค้าเทส"),
        (PRODUCT_TYPE_OLD, "สินค้าเก่า"),
    ]

    sku = models.CharField(max_length=100, verbose_name="SKU")
    name = models.CharField(max_length=255, verbose_name="ชื่อสินค้า")
    image = models.ImageField(upload_to="graphicqueue/products/", null=True, blank=True, verbose_name="รูปสินค้า")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_WAIT, verbose_name="สถานะ")
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default=URGENCY_NORMAL, verbose_name="ประเภทงาน")
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default=PRODUCT_TYPE_TEST, verbose_name="ประเภทสินค้า")

    assignee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"is_graphic": True, "is_active": True},
        related_name="graphic_jobs",
        verbose_name="ผู้รับผิดชอบ",
    )

    order_date = models.DateField(verbose_name="วันที่สั่งงาน")
    deadline = models.DateField(verbose_name="วันเดดไลน์")
    submit_date = models.DateField(null=True, blank=True, verbose_name="วันที่ส่งงาน")
    work_url = models.CharField(max_length=1000, blank=True, verbose_name="URL ลิ้งค์ส่งงาน")

    media_types = models.ManyToManyField(MediaType, blank=True, related_name="jobs", verbose_name="สื่อที่ต้องการทำ")
    media_quantities = models.JSONField(default=dict, blank=True, verbose_name="จำนวนสื่อต่อประเภท")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-order_date", "-created_at"]
        verbose_name = "คิวงานกราฟฟิก"
        verbose_name_plural = "คิวงานกราฟฟิก"

    def __str__(self):
        return f"{self.sku} — {self.name}"

    @property
    def work_days(self):
        if self.order_date and self.submit_date:
            return max((self.submit_date - self.order_date).days, 1)
        return None

    @property
    def status_bg_style(self):
        return {
            self.STATUS_WAIT: "background:#f1f5f9;color:#475569",
            self.STATUS_IN_PROGRESS: "background:#fef3c7;color:#92400e",
            self.STATUS_DONE: "background:#d1fae5;color:#065f46",
        }.get(self.status, "")

    @property
    def urgency_style(self):
        if self.urgency == self.URGENCY_URGENT:
            return "color:#e11d48;font-weight:700"
        return "color:#64748b"


class RefImage(models.Model):
    """Reference image attached to a graphic job, with its own brief text (1-to-1)."""
    job = models.ForeignKey(GraphicJob, on_delete=models.CASCADE, related_name="ref_images")
    image = models.ImageField(upload_to="graphicqueue/refs/")
    brief = models.TextField(blank=True, verbose_name="Brief อธิบายรูป")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Ref {self.pk} for {self.job.sku}"
