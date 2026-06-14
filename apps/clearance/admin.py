from django.contrib import admin
from .models import ClearanceProduct, ClearancePromo


class ClearancePromoInline(admin.TabularInline):
    model = ClearancePromo
    extra = 1
    fields = ("old_price", "new_price", "order")


@admin.register(ClearanceProduct)
class ClearanceProductAdmin(admin.ModelAdmin):
    list_display = ("product_code", "product_name", "status", "assignee", "created_at")
    list_filter = ("status",)
    search_fields = ("product_code", "product_name", "assignee")
    inlines = [ClearancePromoInline]
    readonly_fields = ("created_at", "updated_at")
