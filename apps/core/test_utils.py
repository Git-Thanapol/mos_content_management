"""
Shared test helpers for the MOS CMS test suite.

Usage
-----
from apps.core.test_utils import make_user, make_image
"""
import io
from django.contrib.auth.models import User, Group
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile


# ---------------------------------------------------------------------------
# User factory
# ---------------------------------------------------------------------------

def make_user(username, groups=(), superuser=False, password="testpass123"):
    """
    Create (or get) a User, assign the given Group names, return the user.

    Groups are created if they don't exist yet (mirrors setup_groups behaviour
    so tests don't need to run that management command first).
    """
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={"is_superuser": superuser, "is_staff": superuser},
    )
    user.set_password(password)
    user.is_superuser = superuser
    user.is_staff = superuser
    user.save()
    for gname in groups:
        grp, _ = Group.objects.get_or_create(name=gname)
        user.groups.add(grp)
    return user


# ---------------------------------------------------------------------------
# Image factory (real 1×1 PNG bytes via Pillow so ImageField validation passes)
# ---------------------------------------------------------------------------

def make_image(name="test_image.png"):
    """
    Return a SimpleUploadedFile containing a valid 1×1 white PNG.
    Requires Pillow (already in requirements.txt).
    """
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (1, 1), color=(255, 255, 255))
    img.save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/png")
