from django.urls import path
from . import views

app_name = "clearance"

urlpatterns = [
    # Main list + HTMX table partial
    path("", views.clearance_list, name="clearance_list"),
    path("htmx/rows/", views.clearance_table_partial, name="clearance_table_partial"),

    # Add / edit / delete
    path("add/", views.clearance_form, name="clearance_add"),
    path("<int:pk>/edit/", views.clearance_form, name="clearance_edit"),
    path("<int:pk>/delete/", views.clearance_delete, name="clearance_delete"),

    # Promo modal
    path("<int:pk>/promos/", views.promo_modal, name="promo_modal"),

    # JST HTMX helpers
    path("htmx/jst-search/", views.jst_search, name="jst_search"),
    path("htmx/jst-fields/", views.jst_fields, name="jst_fields"),
]
