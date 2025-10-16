from django.contrib import admin, messages
from .models import Payment

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
