"""
Multi-system access registry and helpers.

Each system has: key, name_th, description, icon, color, url_name, group.
Access is determined by Django group membership (or superuser).
"""
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.conf import settings as django_settings


SYSTEMS = [
    {
        "key": "producttest",
        "name": "Product Test Center",
        "name_th": "ระบบทดสอบสินค้า",
        "description": "บันทึก ติดตาม และวิเคราะห์ผลสินค้าทดสอบก่อนนำเข้าระบบขายจริง",
        "icon": "fa-flask-vial",
        "color": "#4f46e5",
        "color_light": "#eef2ff",
        "color_border": "#c7d2fe",
        "url_name": "product_list",
        "group": "access_producttest",
    },
    {
        "key": "clearance",
        "name": "Clearance Products",
        "name_th": "ระบบสินค้าโล๊ะ",
        "description": "จัดการโปรโมชั่นและลดราคาเพื่อโล๊ะสต็อกสินค้าคงเหลือ",
        "icon": "fa-tags",
        "color": "#ef4444",
        "color_light": "#fff1f2",
        "color_border": "#fecaca",
        "url_name": "clearance:clearance_list",
        "group": "access_clearance",
    },
    {
        "key": "graphicqueue",
        "name": "Graphic Queue Center",
        "name_th": "ระบบคิวงาน Graphic",
        "description": "สั่งงานและติดตามคิวงานกราฟฟิก สื่อคลิปและรูปภาพสำหรับสินค้า",
        "icon": "fa-paintbrush",
        "color": "#4f46e5",
        "color_light": "#eef2ff",
        "color_border": "#c7d2fe",
        "url_name": "graphicqueue:queue_list",
        "group": "access_graphicqueue",
    },
]


def user_can_access(user, key):
    """Return True if the user may access the given system key."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    sys_entry = next((s for s in SYSTEMS if s["key"] == key), None)
    if not sys_entry:
        return False
    return user.groups.filter(name=sys_entry["group"]).exists()


def accessible_systems(user):
    """Return the list of SYSTEMS the user may access."""
    return [s for s in SYSTEMS if user_can_access(user, s["key"])]


def system_required(key):
    """
    View decorator: requires authentication + system access.
    - Unauthenticated → redirect to LOGIN_URL
    - Authenticated but no access → 403 PermissionDenied
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect(f"{django_settings.LOGIN_URL}?next={request.path}")
            if not user_can_access(request.user, key):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
