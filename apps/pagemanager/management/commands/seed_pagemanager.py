"""
Seed default post media types for Page Manager, taken from the customer's
"ระบบ (2).xlsx" sample data. Running again is safe (get_or_create).
Add --flush to clear all existing media types first.

    python manage.py seed_pagemanager
    python manage.py seed_pagemanager --flush
"""
from django.core.management.base import BaseCommand

from apps.pagemanager.models import PostMediaType

MEDIA_TYPES = [
    "อัลบั้ม 4รูป",
    "วิดีโอ 4:5",
    "วิดีโอ 9:16",
    "วิดีโอ 1:1",
    "รูป 1:1",
    "รูป 4:5",
]


class Command(BaseCommand):
    help = "Seed default post media types for Page Manager"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete ALL existing post media types before seeding",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            deleted, _ = PostMediaType.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing media type(s)."))

        count = 0
        for i, name in enumerate(MEDIA_TYPES):
            _, created = PostMediaType.objects.get_or_create(name=name, defaults={"order": i})
            if created:
                count += 1
                self.stdout.write(f"  + {name}")

        self.stdout.write(self.style.SUCCESS(f"Done. {count} new media type(s) created."))
