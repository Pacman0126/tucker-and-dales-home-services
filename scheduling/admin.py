# scheduling/admin.py
from django.contrib import admin
from .models import ServiceCategory, TimeSlot, Employee, Booking, JobAssignment


# Read-only mixin for staff views
class ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser  # only Manager can add

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser  # only Manager can edit

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # only Manager can delete


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    # label-only slots (e.g., "7:30-9:30")
    list_display = ("id", "label")
    search_fields = ("label",)
    ordering = ("label",)


class JobAssignmentInline(admin.TabularInline):
    """
    Inline row(s) of assignments shown under an Employee
    so admins can see where they're scheduled.
    """
    model = JobAssignment
    extra = 0
    fields = ("booking", "jobsite_address")
    autocomplete_fields = ("booking",)
    show_change_link = True


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "service_category", "home_address")
    list_filter = ("service_category",)
    search_fields = ("name", "home_address")
    inlines = [JobAssignmentInline]


@admin.register(Booking)
class BookingAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """
    Keep this aligned with label-only TimeSlot:
    - do NOT reference start_time / end_time anywhere
    - only use fields that actually exist on your uploaded model
    """
    list_display = (
        "id",
        "user",
        "service_category",
        "date",
        "time_slot",
        "status",
        "total_amount",
    )
    list_filter = ("status", "service_category", "date")
    search_fields = ("user__username", "service_address")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user", "service_category", "time_slot", "employee")
    raw_id_fields = ("primary_payment_record",)
