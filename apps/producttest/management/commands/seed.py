"""
Seed the database with the 5 employees and 3 sample products from the mockup,
plus their nested Performance and Commission records.

Usage:
    python manage.py seed
    python manage.py seed --flush    # wipe all app data first
"""
import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from apps.producttest.models import (
    Employee, TestProduct, TestPrice, ProductPage,
    Performance, Commission,
)


EMPLOYEES = [
    {"name": "เบ้น",  "is_graphic": True,  "is_mkt": True},
    {"name": "บอส",  "is_graphic": True,  "is_mkt": False},
    {"name": "มอส",  "is_graphic": True,  "is_mkt": False},
    {"name": "แก้ว", "is_graphic": False, "is_mkt": True},
    {"name": "ฟาง",  "is_graphic": False, "is_mkt": True},
]

PRODUCTS = [
    {
        "pid": "P001",
        "name": "ตู้เครื่องสำอาง",
        "info": "ตู้กระจกสามช่องอเนกประสงค์",
        "detail": "จัดระเบียบ",
        "upload_date": datetime.date(2026, 5, 20),
        "start_date": datetime.date(2026, 5, 21),
        "end_date": datetime.date(2026, 5, 28),
        "manual_status": TestProduct.STATUS_PASS,
        "graphic": ["บอส"],
        "mkt": ["เบ้น"],
        "prices": ["190 บาท"],
        "pages": [{"page": "เพจรีวิว1", "url": "http://fb.com/rev1"}],
        "performance": {"orders": 120, "sales": Decimal("45000"), "ads": Decimal("15000"), "profit": Decimal("12000")},
        "commission": {"total": Decimal("1000"), "status": Commission.STATUS_PAID, "note": "โอนแล้ว"},
    },
    {
        "pid": "P002",
        "name": "เครื่องปั่นไฟฟ้า",
        "info": "รุ่นหัวปั่นสแตนเลส",
        "detail": "เครื่องใช้ไฟฟ้า",
        "upload_date": datetime.date(2026, 5, 22),
        "start_date": datetime.date(2026, 5, 23),
        "end_date": None,
        "manual_status": "",
        "graphic": ["มอส"],
        "mkt": [],
        "prices": [],
        "pages": [],
        "performance": {"orders": 0, "sales": Decimal("0"), "ads": Decimal("0"), "profit": Decimal("0")},
        "commission": {"total": Decimal("0"), "status": Commission.STATUS_WAIT_FILL, "note": ""},
    },
    {
        "pid": "P003",
        "name": "กระเป๋าเดินทาง",
        "info": "ขนาด 20 นิ้ว",
        "detail": "โปรไฟไหม้",
        "upload_date": datetime.date(2026, 5, 25),
        "start_date": datetime.date(2026, 5, 25),
        "end_date": datetime.date(2026, 6, 5),
        "manual_status": TestProduct.STATUS_IN_PROGRESS,
        "graphic": ["บอส", "เบ้น"],
        "mkt": ["แก้ว", "ฟาง"],
        "prices": [],
        "pages": [
            {"page": "Bag Pack Sale", "url": "https://facebook.com/bagpack"},
            {"page": "โปรท่องเที่ยว", "url": "https://facebook.com/travelpro"},
        ],
        "performance": {"orders": 50, "sales": Decimal("25000"), "ads": Decimal("10000"), "profit": Decimal("5000")},
        "commission": {"total": Decimal("0"), "status": Commission.STATUS_WAIT_PAY, "note": "รอรอบบิลหน้า"},
    },
]


class Command(BaseCommand):
    help = "Seed employees, sample products, and auth groups"

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Clear existing data first")

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing app data...")
            CommissionSlip_model = __import__(
                "apps.producttest.models", fromlist=["CommissionSlip"]
            ).CommissionSlip
            CommissionSlip_model.objects.all().delete()
            Commission.objects.all().delete()
            Performance.objects.all().delete()
            ProductPage.objects.all().delete()
            TestPrice.objects.all().delete()
            TestProduct.objects.all().delete()
            Employee.objects.all().delete()

        # Groups
        for name in ["employee", "supervisor"]:
            _, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created group: {name}"))

        # Employees
        emp_map = {}
        for e in EMPLOYEES:
            obj, _ = Employee.objects.update_or_create(
                name=e["name"],
                defaults={"is_graphic": e["is_graphic"], "is_mkt": e["is_mkt"], "is_active": True},
            )
            emp_map[e["name"]] = obj
        self.stdout.write(self.style.SUCCESS(f"  Seeded {len(EMPLOYEES)} employees"))

        # Products
        for pd in PRODUCTS:
            product, _ = TestProduct.objects.update_or_create(
                pid=pd["pid"],
                defaults={
                    "name": pd["name"],
                    "info": pd["info"],
                    "detail": pd["detail"],
                    "upload_date": pd["upload_date"],
                    "start_date": pd["start_date"],
                    "end_date": pd["end_date"],
                    "manual_status": pd["manual_status"],
                },
            )
            product.graphic_members.set([emp_map[n] for n in pd["graphic"] if n in emp_map])
            product.mkt_members.set([emp_map[n] for n in pd["mkt"] if n in emp_map])

            # Prices
            product.prices.all().delete()
            for i, val in enumerate(pd["prices"]):
                TestPrice.objects.create(product=product, value=val, order=i)

            # Pages
            product.pages.all().delete()
            for i, pg in enumerate(pd["pages"]):
                ProductPage.objects.create(product=product, page=pg["page"], url=pg["url"], order=i)

            # Performance
            perf_data = pd["performance"]
            Performance.objects.update_or_create(
                product=product,
                defaults=perf_data,
            )

            # Commission
            comm_data = pd["commission"]
            comm, _ = Commission.objects.update_or_create(
                product=product,
                defaults={
                    "total": comm_data["total"],
                    "status": comm_data["status"],
                    "note": comm_data["note"],
                },
            )

        self.stdout.write(self.style.SUCCESS(f"  Seeded {len(PRODUCTS)} products"))
        self.stdout.write(self.style.SUCCESS("Seed complete. Run 'createsuperuser' to add an admin."))
