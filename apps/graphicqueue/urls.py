from django.urls import path
from . import views

app_name = "graphicqueue"

urlpatterns = [
    path("", views.queue_list, name="queue_list"),
    path("htmx/rows/", views.queue_table_partial, name="queue_table_partial"),
    path("add/", views.queue_form, name="queue_add"),
    path("<int:pk>/edit/", views.queue_form, name="queue_edit"),
    path("<int:pk>/delete/", views.queue_delete, name="queue_delete"),
    path("<int:pk>/media/", views.view_media_modal, name="view_media"),
    path("<int:pk>/ref/", views.view_ref_modal, name="view_ref"),
    path("htmx/media-options/", views.media_options, name="media_options"),
    path("htmx/media-type-add/", views.media_type_add, name="media_type_add"),
]
