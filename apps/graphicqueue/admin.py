from django.contrib import admin
from .models import MediaType, GraphicJob, RefImage


class RefImageInline(admin.TabularInline):
    model = RefImage
    extra = 0
    fields = ("image", "brief", "order")
    readonly_fields = ()


@admin.register(MediaType)
class MediaTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "order")
    list_filter = ("category",)
    search_fields = ("name",)
    ordering = ("category", "order")


@admin.register(GraphicJob)
class GraphicJobAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "status", "urgency", "get_assignees", "order_date", "deadline")
    list_filter = ("status", "urgency", "product_type")
    search_fields = ("sku", "name")
    filter_horizontal = ("media_types", "assignee")
    inlines = [RefImageInline]

    @admin.display(description="Assignee")
    def get_assignees(self, obj):
        return ", ".join(e.name for e in obj.assignee.all())
