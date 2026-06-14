from django.db import models


class ClearanceProduct(models.Model):
    STATUS_WAIT = "รอดำเนินการ"
    STATUS_IN_PROGRESS = "กำลังดำเนินการ"
    STATUS_DONE = "เรียบร้อย"

    STATUS_CHOICES = [
        (STATUS_WAIT, "รอดำเนินการ"),
        (STATUS_IN_PROGRESS, "กำลังดำเนินการ"),
        (STATUS_DONE, "เรียบร้อย"),
    ]

    # JST SKU reference + cached name (for search/display when JST is down)
    product_code = models.CharField(
        max_length=100, db_index=True, verbose_name="รหัสสินค้า (JST)"
    )
    product_name = models.CharField(
        max_length=255, blank=True, verbose_name="ชื่อสินค้า (cached)"
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_WAIT, verbose_name="สถานะ"
    )
    assignee = models.CharField(max_length=100, blank=True, verbose_name="ผู้รับผิดชอบ")
    process_date = models.DateField(null=True, blank=True, verbose_name="วันที่ดำเนินการ")
    done_date = models.DateField(null=True, blank=True, verbose_name="วันที่เรียบร้อย")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "สินค้าโล๊ะ"
        verbose_name_plural = "สินค้าโล๊ะ"

    def __str__(self):
        return f"{self.product_code} — {self.product_name}"

    @property
    def status_bs(self):
        """Bootstrap colour name for status badge."""
        return {
            self.STATUS_WAIT: "secondary",
            self.STATUS_IN_PROGRESS: "warning",
            self.STATUS_DONE: "success",
        }.get(self.status, "secondary")

    @property
    def status_bg_style(self):
        """Inline style background for the mockup's non-Bootstrap colours."""
        return {
            self.STATUS_WAIT: "background:#e0e7ff;color:#3730a3",
            self.STATUS_IN_PROGRESS: "background:#fef3c7;color:#92400e",
            self.STATUS_DONE: "background:#d1fae5;color:#065f46",
        }.get(self.status, "")


class ClearancePromo(models.Model):
    """Old → new price rows for a Clearance product (mirrors mockup promos[])."""
    product = models.ForeignKey(
        ClearanceProduct, on_delete=models.CASCADE, related_name="promos"
    )
    old_price = models.CharField(max_length=255, blank=True, verbose_name="ราคาเดิม")
    new_price = models.CharField(
        max_length=255, blank=True, verbose_name="ราคาใหม่ (ลดล้างสต็อก)"
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.product.product_code}: {self.old_price} → {self.new_price}"
