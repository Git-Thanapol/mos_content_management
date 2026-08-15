import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("producttest", "0002_rename_pang_to_page"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostMediaType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True, verbose_name="ชื่อประเภทสื่อ")),
                ("order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                "verbose_name": "ประเภทสื่อ (โพสต์)",
                "verbose_name_plural": "ประเภทสื่อ (โพสต์)",
                "ordering": ["order", "id"],
            },
        ),
        migrations.CreateModel(
            name="FacebookPage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("page_name", models.CharField(max_length=200, verbose_name="ชื่อเพจ")),
                ("page_id", models.CharField(max_length=50, unique=True, validators=[django.core.validators.RegexValidator("^\\d+$", "กรอกเฉพาะตัวเลขเท่านั้น")], verbose_name="ID PAGE")),
                ("status", models.CharField(choices=[("เพิ่มใหม่", "เพิ่มใหม่"), ("Active ADS", "Active ADS"), ("NON Active", "NON Active"), ("เพจเก่า", "เพจเก่า"), ("ของหมด", "ของหมด"), ("เลิกขาย", "เลิกขาย")], default="เพิ่มใหม่", max_length=30, verbose_name="สถานะ")),
                ("note", models.TextField(blank=True, verbose_name="หมายเหตุ")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owners", models.ManyToManyField(blank=True, related_name="managed_pages", to="producttest.employee", verbose_name="ผู้ดูแลเพจ")),
            ],
            options={
                "verbose_name": "เพจ Facebook",
                "verbose_name_plural": "เพจ Facebook",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PageSKU",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_code", models.CharField(max_length=100, verbose_name="รหัสสินค้า (JST)")),
                ("product_name", models.CharField(blank=True, max_length=255, verbose_name="ชื่อสินค้า (cached)")),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("page", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="skus", to="pagemanager.facebookpage")),
            ],
            options={
                "ordering": ["order", "id"],
                "unique_together": {("page", "product_code")},
            },
        ),
        migrations.CreateModel(
            name="PagePost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(blank=True, null=True, upload_to="pagemanager/posts/", verbose_name="รูป")),
                ("product_code", models.CharField(blank=True, max_length=100, verbose_name="รหัสสินค้า (JST)")),
                ("product_name", models.CharField(blank=True, max_length=255, verbose_name="ชื่อสินค้า (cached)")),
                ("post_id", models.CharField(max_length=50, validators=[django.core.validators.RegexValidator("^\\d+$", "กรอกเฉพาะตัวเลขเท่านั้น")], verbose_name="ID POST")),
                ("post_date", models.DateField(verbose_name="วันที่ลงสื่อ")),
                ("note", models.TextField(blank=True, verbose_name="หมายเหตุ")),
                ("supervisor_note", models.TextField(blank=True, verbose_name="ข้อมูลหมายเหตุ เฉพาะหัวหน้า")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("media_type", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="posts", to="pagemanager.postmediatype", verbose_name="ประเภทสื่อ")),
                ("page", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="posts", to="pagemanager.facebookpage")),
                ("poster", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="page_posts", to="producttest.employee", verbose_name="ผู้ลงโพส")),
            ],
            options={
                "verbose_name": "โพสต์เพจ",
                "verbose_name_plural": "โพสต์เพจ",
                "ordering": ["post_date", "id"],
            },
        ),
    ]
