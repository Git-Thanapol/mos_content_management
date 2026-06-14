from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .access import accessible_systems


@login_required
def hub(request):
    """Landing page: shows the systems a user can access as clickable cards."""
    systems = accessible_systems(request.user)
    return render(request, "core/hub.html", {"systems": systems})
