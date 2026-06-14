from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    # System apps — namespaced paths
    path("producttest/", include("apps.producttest.urls")),
    path("clearance/", include("apps.clearance.urls")),
    path("graphicqueue/", include("apps.graphicqueue.urls")),
    # Hub at root (must be last — catches "" after the above)
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
