from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User


class Employee(models.Model):
    name = models.CharField(max_length=100, unique=True)
    nickname = models.CharField(max_length=100, blank=True, verbose_name="ชื่อเล่น")
    is_graphic = models.BooleanField(default=False, verbose_name="ตำแหน่ง Graphic")
    is_mkt = models.BooleanField(default=False, verbose_name="ตำแหน่ง MKT")
    is_active = models.BooleanField(default=True)
    # Phase 5: link to auth.User
    user = models.OneToOneField(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="employee"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TestProduct(models.Model):
    STATUS_AUTO = ""
    STATUS_IN_PROGRESS = "กำลังดำเนินการ"
    STATUS_PASS = "Test ผ่าน"
    STATUS_FAIL = "Test ไม่ผ่าน"
    STATUS_CANCEL = "ยกเลิก"

    MANUAL_STATUS_CHOICES = [
        (STATUS_AUTO, "อัตโนมัติ (ระบบจัดการ)"),
        (STATUS_IN_PROGRESS, "กำลังดำเนินการ"),
        (STATUS_PASS, "Test ผ่าน"),
        (STATUS_FAIL, "Test ไม่ผ่าน"),
        (STATUS_CANCEL, "ยกเลิก"),
    ]

    pid = models.CharField(max_length=50, unique=True, verbose_name="Product ID")
    name = models.CharField(max_length=255, verbose_name="ชื่อสินค้า")
    info = models.TextField(blank=True, verbose_name="ข้อมูลสินค้า")
    detail = models.TextField(blank=True, verbose_name="รายละเอียดการทำงาน / หมายเหตุ")
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    upload_date = models.DateField(verbose_name="วันที่ลงข้อมูล")
    start_date = models.DateField(verbose_name="วันที่เริ่มทดสอบ")
    end_date = models.DateField(null=True, blank=True, verbose_name="วันที่สิ้นสุดทดสอบ")
    manual_status = models.CharField(
        max_length=30,
        choices=MANUAL_STATUS_CHOICES,
        blank=True,
        default="",
        verbose_name="สถานะ (ปรับโดยหัวหน้า)",
    )
    graphic_members = models.ManyToManyField(
        Employee,
        blank=True,
        related_name="graphic_products",
        limit_choices_to={"is_active": True, "is_graphic": True},
        verbose_name="Graphic",
    )
    mkt_members = models.ManyToManyField(
        Employee,
        blank=True,
        related_name="mkt_products",
        limit_choices_to={"is_active": True, "is_mkt": True},
        verbose_name="MKT",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-upload_date", "-created_at"]

    def __str__(self):
        return f"{self.pid} — {self.name}"

    def computed_status(self):
        """Replicates getComputedStatus() from the mockup (line 1112-1116).

        Locked manual statuses take precedence; otherwise derive from members.
        """
        locked = {self.STATUS_IN_PROGRESS, self.STATUS_PASS, self.STATUS_FAIL, self.STATUS_CANCEL}
        if self.manual_status in locked:
            return self.manual_status
        has_members = (
            self.graphic_members.exists() or self.mkt_members.exists()
        )
        return "กำลังดำเนินการ" if has_members else "รอดำเนินการ"

    def test_days(self):
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            return max(delta.days, 1)
        return None

    def member_count(self):
        return self.graphic_members.count() + self.mkt_members.count()


class TestPrice(models.Model):
    product = models.ForeignKey(TestProduct, on_delete=models.CASCADE, related_name="prices")
    value = models.CharField(max_length=100, verbose_name="ราคาทดสอบ")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.product.pid}: {self.value}"


class ProductPage(models.Model):
    product = models.ForeignKey(TestProduct, on_delete=models.CASCADE, related_name="pages")
    page = models.CharField(max_length=255, blank=True, verbose_name="PAGE")
    url = models.CharField(max_length=500, blank=True, verbose_name="URL")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.product.pid}: {self.page}"


class Performance(models.Model):
    product = models.OneToOneField(
        TestProduct, on_delete=models.CASCADE, related_name="performance"
    )
    orders = models.PositiveIntegerField(default=0, verbose_name="จำนวนออเดอร์")
    sales = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name="ยอดขาย"
    )
    ads = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name="ค่าโฆษณา"
    )
    profit = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name="กำไร"
    )

    @property
    def ads_pct(self):
        if self.sales and self.sales > 0:
            return round(float(self.ads / self.sales) * 100, 2)
        return 0.0

    @property
    def profit_pct(self):
        if self.sales and self.sales > 0:
            return round(float(self.profit / self.sales) * 100, 2)
        return 0.0

    @property
    def profit_is_negative(self):
        return self.profit < Decimal("0")

    def __str__(self):
        return f"Performance: {self.product.pid}"


class Commission(models.Model):
    STATUS_WAIT_FILL = "รอกรอกค่าคอม"
    STATUS_WAIT_PAY = "รอจ่ายค่าคอม"
    STATUS_PAID = "จ่ายค่าคอมเรียบร้อย"

    STATUS_CHOICES = [
        (STATUS_WAIT_FILL, "รอกรอกค่าคอม"),
        (STATUS_WAIT_PAY, "รอจ่ายค่าคอม"),
        (STATUS_PAID, "จ่ายค่าคอมเรียบร้อย"),
    ]

    product = models.OneToOneField(
        TestProduct, on_delete=models.CASCADE, related_name="commission"
    )
    total = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name="ยอดรวมค่าคอม"
    )
    per_person = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name="ค่าคอมต่อคน"
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_WAIT_FILL,
        verbose_name="สถานะค่าคอม",
    )
    note = models.CharField(max_length=255, blank=True, verbose_name="หมายเหตุ")

    def recalculate_per_person(self):
        count = self.product.member_count()
        self.per_person = self.total / count if count > 0 else Decimal("0")

    def save(self, *args, **kwargs):
        self.recalculate_per_person()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Commission: {self.product.pid} ({self.status})"


class CommissionSlip(models.Model):
    commission = models.ForeignKey(
        Commission, on_delete=models.CASCADE, related_name="slips"
    )
    image = models.ImageField(upload_to="slips/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Slip for {self.commission.product.pid}"
