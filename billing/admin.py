from django.contrib import admin, messages
from .models import Payment, PaymentHistory

# Register your models here.


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "amount_display",
                    "currency", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("user__username", "stripe_payment_intent_id")
    ordering = ("-created_at",)
    actions = ["issue_refund"]

    @admin.action(description="Issue Stripe refund for selected payments")
    def issue_refund(self, request, queryset):
        success = 0
        fail = 0
        for payment in queryset:
            try:
                if payment.status == "succeeded":
                    payment.refund()
                    success += 1
                else:
                    fail += 1
            except Exception as e:
                self.message_user(
                    request, f"Refund failed for {payment}: {e}", level=messages.ERROR)
                fail += 1

        if success:
            self.message_user(
                request, f"✅ {success} refund(s) completed successfully.", level=messages.SUCCESS)
        if fail:
            self.message_user(
                request, f"⚠️ {fail} refund(s) could not be processed.", level=messages.WARNING)


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "stripe_payment_id", "service_address")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)

    fieldsets = (
        ("Transaction Info", {
            "fields": (
                "user",
                "amount",
                "currency",
                "status",
                "notes",
            )
        }),
        ("Stripe / Metadata", {
            "fields": ("stripe_payment_id", "raw_data"),
        }),
        ("Timestamps", {
            "fields": ("created_at",),
        }),
    )


@admin.display(description="Chain Totals")
def chain_summary(obj):
    o, a, c, n = obj.compute_sections()
    return f"Orig: ${o:.2f} | +${a:.2f} | {c:.2f} | Net: ${n:.2f}"


# @admin.register(PaymentHistory)
# class PaymentHistoryAdmin(admin.ModelAdmin):
#     list_display = ("id", "user", "status", "amount",
#                     "service_address", "chain_summary", "created_at")
#     readonly_fields = ("created_at",)
#     def chain_summary(self, obj): return chain_summary(obj)
