from django.contrib import admin
from .models import Payment

# Register your models here.


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "amount_display",
                    "currency", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("user__username", "stripe_payment_intent_id")
    ordering = ("-created_at",)
