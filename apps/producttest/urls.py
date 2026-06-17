from django.urls import path
from . import views

urlpatterns = [
    # Main page + HTMX table partial
    path("", views.product_list, name="product_list"),
    path("htmx/products/", views.product_table_partial, name="product_table_partial"),

    # Add / edit product modal
    path("products/add/", views.product_form, name="product_add"),
    path("products/<int:pk>/edit/", views.product_form, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),

    # Test prices
    path("products/<int:pk>/prices/", views.product_prices, name="product_prices"),

    # Pages
    path("products/<int:pk>/pages/", views.product_pages, name="product_pages"),

    # Info / media popup (read-only)
    path("products/<int:pk>/info/", views.product_info, name="product_info"),

    # Supervisor
    path("supervisor/", views.supervisor_view, name="supervisor"),
    path("htmx/supervisor/", views.supervisor_table_partial, name="supervisor_table_partial"),
    path("supervisor/<int:pk>/manage/", views.supervisor_manage, name="supervisor_manage"),

    # Personal report (locked to current logged-in user)
    path("report/", views.personal_report, name="personal_report"),
    path("htmx/report/", views.report_table_partial, name="report_table_partial"),
]
