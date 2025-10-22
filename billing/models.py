from decimal import Decimal
from datetime import datetime as dt
from typing import TYPE_CHECKING
from django.utils.timezone import now


from django.conf import settings
from django.db import models
import stripe

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

    def refund(self):
        """
        Initiates a Stripe refund for this payment.
        Returns the refund object or raises an exception if fails.
        """
        if not self.stripe_payment_intent_id:
            raise ValueError(
                "No Stripe payment intent ID associated with this payment.")

        stripe.api_key = settings.STRIPE_SECRET_KEY

        refund = stripe.Refund.create(
            payment_intent=self.stripe_payment_intent_id,
            reason="requested_by_customer",
        )

        # update model state
        self.status = "refunded"
        self.metadata["refund_id"] = refund.id
        self.save(update_fields=["status", "metadata"])
        return refund


class CartManager(models.Manager):
    """
    Centralized helper to fetch or create a cart
    for the current request (user or anonymous session).
    """

    def get_for_request(self, request):
        # Ensure session exists
        if not request.session.session_key:
            request.session.save()

        if request.user.is_authenticated:
            cart, _ = self.get_or_create(user=request.user)
        else:
            cart, _ = self.get_or_create(
                session_key=request.session.session_key)

        return cart


class Cart(models.Model):
    """
    Represents a booking or shopping cart for a single customer session.
    Each cart is tied to either a logged-in user or an anonymous session_key,
    and optionally to a normalized address_key for address-based isolation.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="carts",
    )

    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        db_index=True,
        help_text="Anonymous session identifier for guests.",
    )

    address_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text="Normalized address string for session-level cart isolation.",
    )

    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        from billing.models import CartItem
        items: "models.Manager[CartItem]"

    class Meta:
        indexes = [
            models.Index(fields=["session_key"]),
            models.Index(fields=["user"]),
            models.Index(fields=["address_key"]),
        ]
        ordering = ["-updated_at"]

    def __str__(self):
        owner = self.user or self.session_key or "anonymous"
        return f"Cart<{owner}>"

    # ----------------------------------------------------
    # 💲 Computed Totals
    # ----------------------------------------------------
    @property
    def subtotal(self) -> Decimal:
        """Sum of all item subtotals (PRE-TAX)."""
        total = sum(
            (item.subtotal for item in self.items.all()),
            Decimal("0.00"),
        )
        return total.quantize(Decimal("0.01"))

    @property
    def tax(self) -> Decimal:
        """Tax computed once on subtotal."""
        from billing.constants import SALES_TAX_RATE
        tax_rate = Decimal(str(SALES_TAX_RATE))
        return (self.subtotal * tax_rate).quantize(Decimal("0.01"))

    @property
    def total(self) -> Decimal:
        """Grand total = subtotal + tax."""
        return (self.subtotal + self.tax).quantize(Decimal("0.01"))

    # ----------------------------------------------------
    # 🧹 Utilities
    # ----------------------------------------------------
    def clear(self):
        """Remove all items from this cart."""
        self.items.all().delete()

    @property
    def item_count(self) -> int:
        """Convenience property for navbar badge count."""
        return self.items.count()

    def has_items(self) -> bool:
        """Return True if the cart has any items."""
        return self.items.exists()


class CartItem(models.Model):
    """
    One service assignment the customer intends to book.
    Uniqueness prevents duplicate same-slot/employee entries in the same cart.
    """
    cart = models.ForeignKey(
        "billing.Cart",
        on_delete=models.CASCADE,
        related_name="items",          # enables cart.items.all()
    )
    service_category = models.ForeignKey(
        "scheduling.ServiceCategory",
        on_delete=models.PROTECT,      # prevent deletion if still referenced
    )
    time_slot = models.ForeignKey(
        "scheduling.TimeSlot",
        on_delete=models.PROTECT,
    )
    employee = models.ForeignKey(
        "scheduling.Employee",
        on_delete=models.PROTECT,
    )
    date = models.DateField()

    # --- Pricing fields ---
    unit_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Stored as PRE-TAX price per 2-hour service block.",
    )
    quantity = models.PositiveIntegerField(default=1)

    # --- Metadata ---
    created_at = models.DateTimeField(default=now)

    class Meta:
        unique_together = (
            ("cart", "service_category", "time_slot", "date", "employee"),
        )

    def __str__(self):
        return f"{self.service_category} | {self.date} {self.time_slot} | {self.employee}"

    @property
    def subtotal(self) -> Decimal:
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))
