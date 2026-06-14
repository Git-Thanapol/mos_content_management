from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Employee, TestProduct, TestPrice, ProductPage,
    Performance, Commission, CommissionSlip,
)


# ── Employee inline on User admin ─────────────────────────────────────────────

class EmployeeInline(admin.StackedInline):
    model = Employee
    can_delete = False
    verbose_name = "โปรไฟล์พนักงาน"
    verbose_name_plural = "โปรไฟล์พนักงาน"
    fields = ["name", "nickname", "is_graphic", "is_mkt", "is_active"]
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = [EmployeeInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# ── Product Test admin ────────────────────────────────────────────────────────

class TestPriceInline(admin.TabularInline):
    model = TestPrice
    extra = 1


class ProductPageInline(admin.TabularInline):
    model = ProductPage
    extra = 1


class PerformanceInline(admin.StackedInline):
    model = Performance
    can_delete = False


class CommissionInline(admin.StackedInline):
    model = Commission
    can_delete = False


@admin.register(TestProduct)
class TestProductAdmin(admin.ModelAdmin):
    list_display = ["pid", "name", "upload_date", "start_date", "end_date", "manual_status"]
    list_filter = ["manual_status", "upload_date"]
    search_fields = ["pid", "name"]
    filter_horizontal = ["graphic_members", "mkt_members"]
    inlines = [TestPriceInline, ProductPageInline, PerformanceInline, CommissionInline]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["name", "nickname", "is_graphic", "is_mkt", "is_active", "user"]
    list_filter = ["is_graphic", "is_mkt", "is_active"]
    search_fields = ["name", "nickname"]


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ["product", "total", "per_person", "status"]
    list_filter = ["status"]


admin.site.register(CommissionSlip)
admin.site.register(Performance)
