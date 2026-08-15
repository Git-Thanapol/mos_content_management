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
