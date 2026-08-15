"""
Row-level visibility helpers for Page Manager.

Non-supervisor employees may only see pages they are listed as an owner of.
Supervisors (and superusers) see everything. Every view/export must filter
through visible_pages() — never query FacebookPage.objects.all() directly.
"""
from .models import FacebookPage


def is_supervisor(user):
    return user.is_superuser or user.groups.filter(name="supervisor").exists()


def visible_pages(user):
    qs = FacebookPage.objects.all()
    if is_supervisor(user):
        return qs
    emp = getattr(user, "employee", None)
    if emp is None:
        return qs.none()
    return qs.filter(owners=emp).distinct()
