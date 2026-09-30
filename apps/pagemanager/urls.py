from django.urls import path

from . import exports, views

app_name = "pagemanager"

urlpatterns = [
    # Pages
    path("", views.page_list, name="page_list"),
    path("htmx/rows/", views.page_table_partial, name="page_table_partial"),
    path("add/", views.page_form, name="page_add"),
    path("<int:pk>/edit/", views.page_form, name="page_edit"),
    path("<int:pk>/delete/", views.page_delete, name="page_delete"),
    path("htmx/jst-search/", views.jst_search, name="jst_search"),
    path("htmx/media-type-add/", views.media_type_add, name="media_type_add"),

    # Category / ADS / STOCK
    path("htmx/categories/", views.category_modal, name="category_modal"),
    path("htmx/categories/add/", views.category_add, name="category_add"),
    path("htmx/categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("<int:pk>/category/", views.page_category_set, name="page_category_set"),
    path("<int:pk>/ads/", views.ads_modal, name="ads_modal"),
    path("<int:pk>/ads/save/", views.ads_save, name="ads_save"),
    path("<int:pk>/ads/<int:ads_pk>/delete/", views.ads_delete, name="ads_delete"),
    path("<int:pk>/stock/", views.stock_list, name="stock_list"),
    path("<int:pk>/stock/htmx/body/", views.stock_body, name="stock_body"),
    path("<int:pk>/stock/add/", views.stock_add, name="stock_add"),
    path("<int:pk>/stock/<int:item_pk>/update/", views.stock_update, name="stock_update"),
    path("<int:pk>/stock/<int:item_pk>/delete/", views.stock_delete, name="stock_delete"),

    # Exports
    path("export/pages/", exports.export_pages, name="export_pages"),
    path("export/posts/", exports.export_all_posts, name="export_all_posts"),

    # Posts (scoped under a page)
    path("<int:page_pk>/posts/", views.post_list, name="post_list"),
    path("<int:page_pk>/posts/htmx/rows/", views.post_table_partial, name="post_table_partial"),
    path("<int:page_pk>/posts/add/", views.post_form, name="post_add"),
    path("<int:page_pk>/posts/<int:pk>/edit/", views.post_form, name="post_edit"),
    path("<int:page_pk>/posts/<int:pk>/delete/", views.post_delete, name="post_delete"),
    path("<int:page_pk>/export/posts/", exports.export_page_posts, name="export_page_posts"),
]
