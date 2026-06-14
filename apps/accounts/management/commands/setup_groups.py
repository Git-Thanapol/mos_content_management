from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


GROUPS = [
    # Role groups (producttest system)
    "employee",
    "supervisor",
    # System-access groups (one per app; superusers bypass these)
    "access_producttest",
    "access_clearance",
    "access_graphicqueue",
]


class Command(BaseCommand):
    help = "Create default auth groups for all systems"

    def handle(self, *args, **options):
        for name in GROUPS:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created group: {name}"))
            else:
                self.stdout.write(f"  Already exists: {name}")
        self.stdout.write(self.style.SUCCESS("Done. Assign groups to users in /admin."))
