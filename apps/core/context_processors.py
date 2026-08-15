from .access import accessible_systems


def available_systems(request):
    """
    Inject available_systems and active_system into every template context.
    - available_systems: list of SYSTEMS dicts the user may access
    - active_system: key string of the currently active system, or None
    """
    systems = accessible_systems(request.user) if request.user.is_authenticated else []

    # Detect active system from URL path
    active = None
    path = request.path
    if path.startswith("/clearance/"):
        active = "clearance"
    elif path.startswith("/producttest/"):
        active = "producttest"
    elif path.startswith("/graphicqueue/"):
        active = "graphicqueue"
    elif path.startswith("/pagemanager/"):
        active = "pagemanager"

    return {
        "available_systems": systems,
        "active_system": active,
    }
