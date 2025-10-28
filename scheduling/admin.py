from django.contrib import admin
from .models import Booking, TimeSlot, ServiceCategory, Employee
# Register your models here.


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "service_category",
        "employee",
        "date",
        "time_slot",
        "status",
        "total_amount",
    )
    list_filter = ("status", "service_category", "date")
    search_fields = ("user__username", "service_address")
    date_hierarchy = "date"
    readonly_fields = ("created_at", "updated_at")

    # 🧾 show linked payments directly in the Booking detail page
    def view_payment_links(self, obj):
        if not hasattr(obj, "payment_history"):
            return "—"
        payments = obj.payment_history.all()
        if not payments.exists():
            return "—"
        html = "<ul>"
        for p in payments:
            html += (
                f"<li>${p.amount:.2f} ({p.status}) — "
                f"<a href='/admin/billing/paymenthistory/{p.id}/change/'>View</a></li>"
            )
        html += "</ul>"
        return html

    view_payment_links.short_description = "Linked Payments"
    view_payment_links.allow_tags = True

    fieldsets = (
        ("Customer & Scheduling", {
            "fields": (
                "user",
                "service_address",
                "service_category",
                "employee",
                "date",
                "time_slot",
            )
        }),
        ("Payment Info", {
            "fields": ("unit_price", "total_amount", "view_payment_links"),
        }),
        ("Status & Meta", {
            "fields": ("status", "created_at", "updated_at"),
        }),
    )

    readonly_fields = ("view_payment_links", "created_at", "updated_at")
