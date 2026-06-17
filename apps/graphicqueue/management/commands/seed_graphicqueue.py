"""
Seed default media types for the Graphic Queue.
Running again is safe (get_or_create).
Add --flush to clear all existing media types first.

    python manage.py seed_graphicqueue
    python manage.py seed_graphicqueue --flush
"""
from django.core.management.base import BaseCommand
from apps.graphicqueue.models import MediaType


VIDEO_TYPES = [
    "คลิป 1:1 (มีกรอบ)",
    "คลิป 1:1 (ไม่มีกรอบ)",
    "คลิป 4:5 (มีกรอบ)",
    "คลิป 4:5 (ไม่มีกรอบ)",
    "คลิป 9:16 (มีกรอบ)",
    "คลิป 9:16 (ไม่มีกรอบ)",
]

IMAGE_TYPES = [
    "ภาพ 1 ภาพ 4:5",
    "ภาพ 1 ภาพ 9:16",
    "ภาพ อัลบั้ม 4 ภาพ 1:1",
]


class Command(BaseCommand):
    help = "Seed default media types (6 video + 3 image) for the Graphic Queue"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete ALL existing media types before seeding (M2M links will be cleared)",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            deleted, _ = MediaType.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing media type(s)."))

        count = 0
        for i, name in enumerate(VIDEO_TYPES):
            _, created = MediaType.objects.get_or_create(
                name=name,
                defaults={"category": MediaType.CATEGORY_VIDEO, "order": i},
            )
            if created:
                count += 1
                self.stdout.write(f"  + [คลิป] {name}")

        for i, name in enumerate(IMAGE_TYPES):
            _, created = MediaType.objects.get_or_create(
                name=name,
                defaults={"category": MediaType.CATEGORY_IMAGE, "order": i},
            )
            if created:
                count += 1
                self.stdout.write(f"  + [ภาพ] {name}")

        self.stdout.write(self.style.SUCCESS(f"Done. {count} new media type(s) created."))
