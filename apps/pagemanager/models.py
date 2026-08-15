from django.core.validators import RegexValidator
from django.db import models

from apps.producttest.models import Employee

numeric_id_validator = RegexValidator(r"^\d+$", "กรอกเฉพาะตัวเลขเท่านั้น")


class FacebookPage(models.Model):
    STATUS_NEW = "เพิ่มใหม่"
    STATUS_ACTIVE = "Active ADS"
    STATUS_NON_ACTIVE = "NON Active"
    STATUS_OLD = "เพจเก่า"
    STATUS_SOLD_OUT = "ของหมด"
    STATUS_DISCONTINUED = "เลิกขาย"

    STATUS_CHOICES = [
        (STATUS_NEW, "เพิ่มใหม่"),
        (STATUS_ACTIVE, "Active ADS"),
        (STATUS_NON_ACTIVE, "NON Active"),
        (STATUS_OLD, "เพจเก่า"),
        (STATUS_SOLD_OUT, "ของหมด"),
        (STATUS_DISCONTINUED, "เลิกขาย"),
    ]

    page_name = models.CharField(max_length=200, verbose_name="ชื่อเพจ")
    page_id = models.CharField(
        max_length=50,
        unique=True,
        validators=[numeric_id_validator],
        verbose_name="ID PAGE",
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=STATUS_NEW, verbose_name="สถานะ"
    )
    owners = models.ManyToManyField(
        Employee,
        blank=True,
        related_name="managed_pages",
        verbose_name="ผู้ดูแลเพจ",
    )
    note = models.TextField(blank=True, verbose_name="หมายเหตุ")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "เพจ Facebook"
        verbose_name_plural = "เพจ Facebook"

    def __str__(self):
        return f"{self.page_name} ({self.page_id})"

    @property
    def status_bg_style(self):
        return {
            self.STATUS_NEW: "background:#ffe3e3;color:#c92a2a",
            self.STATUS_ACTIVE: "background:#d3f9d8;color:#2b8a3e",
            self.STATUS_NON_ACTIVE: "background:#fff3bf;color:#e67700",
            self.STATUS_OLD: "background:#ffe8d9;color:#d9480f",
            self.STATUS_SOLD_OUT: "background:#f3e8ff;color:#6741d9",
            self.STATUS_DISCONTINUED: "background:#e9ecef;color:#495057",
        }.get(self.status, "")

    @property
    def chat_url(self):
        return f"https://www.facebook.com/latest/inbox/all?asset_id={self.page_id}"

    @property
    def page_url(self):
        return f"https://www.facebook.com/{self.page_id}"


class PageSKU(models.Model):
    page = models.ForeignKey(FacebookPage, on_delete=models.CASCADE, related_name="skus")
    product_code = models.CharField(max_length=100, verbose_name="รหัสสินค้า (JST)")
    product_name = models.CharField(max_length=255, blank=True, verbose_name="ชื่อสินค้า (cached)")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("page", "product_code")

    def __str__(self):
        return f"{self.page.page_name}: {self.product_code}"


class PostMediaType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="ชื่อประเภทสื่อ")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "ประเภทสื่อ (โพสต์)"
        verbose_name_plural = "ประเภทสื่อ (โพสต์)"

    def __str__(self):
        return self.name


class PagePost(models.Model):
    page = models.ForeignKey(FacebookPage, on_delete=models.CASCADE, related_name="posts")
    image = models.ImageField(upload_to="pagemanager/posts/", null=True, blank=True, verbose_name="รูป")
    poster = models.ForeignKey(
        Employee, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="page_posts", verbose_name="ผู้ลงโพส",
    )
    product_code = models.CharField(max_length=100, blank=True, verbose_name="รหัสสินค้า (JST)")
    product_name = models.CharField(max_length=255, blank=True, verbose_name="ชื่อสินค้า (cached)")
    media_type = models.ForeignKey(
        PostMediaType, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="posts", verbose_name="ประเภทสื่อ",
    )
    post_id = models.CharField(
        max_length=50, validators=[numeric_id_validator], verbose_name="ID POST"
    )
    post_date = models.DateField(verbose_name="วันที่ลงสื่อ")
    note = models.TextField(blank=True, verbose_name="หมายเหตุ")
    supervisor_note = models.TextField(blank=True, verbose_name="ข้อมูลหมายเหตุ เฉพาะหัวหน้า")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["post_date", "id"]
        verbose_name = "โพสต์เพจ"
        verbose_name_plural = "โพสต์เพจ"

    def __str__(self):
        return f"{self.page.page_name}: {self.post_id}"

    @property
    def post_url(self):
        return f"https://www.facebook.com/{self.post_id}"
