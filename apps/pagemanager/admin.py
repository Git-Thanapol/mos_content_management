from django.contrib import admin

from .models import FacebookPage, PagePost, PageSKU, PostMediaType


class PageSKUInline(admin.TabularInline):
    model = PageSKU
    extra = 0
    fields = ("product_code", "product_name", "order")


class PagePostInline(admin.TabularInline):
    model = PagePost
    extra = 0
    fields = ("post_id", "poster", "product_code", "media_type", "post_date")


@admin.register(FacebookPage)
class FacebookPageAdmin(admin.ModelAdmin):
    list_display = ("page_name", "page_id", "status", "get_owners", "created_at")
    list_filter = ("status",)
    search_fields = ("page_name", "page_id")
    filter_horizontal = ("owners",)
    inlines = [PageSKUInline, PagePostInline]
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="ผู้ดูแล")
    def get_owners(self, obj):
        return ", ".join(e.name for e in obj.owners.all())


@admin.register(PostMediaType)
class PostMediaTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    ordering = ("order",)
