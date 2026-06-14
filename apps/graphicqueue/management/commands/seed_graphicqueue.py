"""
Seed the 10 default media types from the mockup into the MediaType catalog.
Running this again is safe (get_or_create).

    python manage.py seed_graphicqueue
"""
from django.core.management.base import BaseCommand
from apps.graphicqueue.models import MediaType


VIDEO_TYPES = [
    "คลิป 1:1 (มีกรอบข้อมูล)",
    "คลิป 9:16 (มีกรอบข้อมูล)",
    "คลิป 1:1 (ไม่มีกรอบ)",
    "คลิป 9:16 (ไม่มีกรอบ) - แบบ 1",
    "คลิป 9:16 (ไม่มีกรอบ) - แบบ 2",
]

IMAGE_TYPES = [
    "ภาพ อัลบั้ม 4 ภาพ 1:1 (เซ็ต 1)",
    "ภาพ อัลบั้ม 4 ภาพ 1:1 (เซ็ต 2)",
    "ภาพ อัลบั้ม 4 ภาพ 1:1 (เซ็ต 3)",
    "ภาพ อัลบั้ม 4 ภาพ 1:1 (เซ็ต 4)",
    "ภาพ อัลบั้ม 4 ภาพ 1:1 (เซ็ต 5)",
]


class Command(BaseCommand):
    help = "Seed 10 default media types (5 video + 5 image) for the Graphic Queue"

    def handle(self, *args, **options):
        count = 0
        for i, name in enumerate(VIDEO_TYPES):
            _, created = MediaType.objects.get_or_create(
                name=name,
                defaults={"category": MediaType.CATEGORY_VIDEO, "order": i},
            )
            if created:
                count += 1
                self.stdout.write(f"  + {name}")

        for i, name in enumerate(IMAGE_TYPES):
            _, created = MediaType.objects.get_or_create(
                name=name,
                defaults={"category": MediaType.CATEGORY_IMAGE, "order": i},
            )
            if created:
                count += 1
                self.stdout.write(f"  + {name}")

        self.stdout.write(self.style.SUCCESS(f"Done. {count} new media types created."))
