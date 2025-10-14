from django.conf import settings
from django.db import models

# Create your models here.


class Payment(models.Model):
    """Stores individual Stripe payment records."""

    class Status(models.TextChoices):
        REQUIRES_PAYMENT_METHOD = "requires_payment_method"
        REQUIRES_CONFIRMATION = "requires_confirmation"
        REQUIRES_ACTION = "requires_action"
        PROCESSING = "processing"
        SUCCEEDED = "succeeded"
        CANCELED = "canceled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.IntegerField(help_text="Amount in cents")
    currency = models.CharField(max_length=10, default="usd")

    stripe_payment_intent_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    stripe_checkout_session_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PROCESSING
    )

    description = models.CharField(max_length=255, blank=True)
    receipt_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def amount_display(self):
        """Readable currency string."""
        return f"${self.amount / 100:.2f}"

    def __str__(self):
        return f"{self.user} — {self.amount_display()} — {self.status}"
