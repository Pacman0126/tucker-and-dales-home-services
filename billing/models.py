from django.utils import timezone
from decimal import Decimal
from datetime import datetime as dt
from typing import TYPE_CHECKING
from django.utils.timezone import now
from django.core.mail import send_mail

from django.conf import settings
from django.db import models
import stripe


from scheduling.models import Booking
if TYPE_CHECKING:
    from django.http import HttpRequest

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


class CartManager(models.Manager["Cart"]):
    """Custom manager with helper for resolving current user's or session's cart."""

    def get_for_request(self, request: "HttpRequest"):
        """
        Return the active cart for this request (user or session-based).
        Creates one if none exists.
        """
        from billing.models import Cart  # local import to avoid circulars

        if not request.session.session_key:
            request.session.create()

        address_key = request.session.get("service_address", "")
        lookup = {"address_key": address_key}

        if request.user.is_authenticated:
            lookup["user"] = request.user
        else:
            lookup["session_key"] = request.session.session_key

        cart, _ = Cart.objects.get_or_create(**lookup)
        return cart


class Cart(models.Model):
    """
    Represents a booking or shopping cart for a single customer session.
    Each cart is tied to either a logged-in user or an anonymous session_key,
    and optionally to a normalized address_key for address-based isolation.
    """

    objects: CartManager = CartManager()

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
        constraints = [
            models.UniqueConstraint(
                fields=["user", "session_key", "address_key"],
                name="unique_user_session_address_cart"
            )
        ]

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

    # 🏠 Service address (critical for live invoice + history tracking)
    service_address = models.CharField(
        max_length=255,
        help_text="Full street address where this service is performed.",
        default="Unknown"
    )

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


class PaymentHistory(models.Model):
    STATUS_CHOICES = [
        ("Paid", "Paid"),
        ("Cancelled", "Cancelled"),
        ("Refunded", "Refunded"),
        ("Adjustment", "Adjustment"),
    ]

    linked_bookings = models.ManyToManyField(
        "scheduling.Booking",
        related_name="linked_payment_records",
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    booking = models.ForeignKey(
        "scheduling.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_payment_records",
        help_text="All payment records associated with this booking."
    )
    parent = models.ForeignKey(  # ✅ for invoice chain logic
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="adjustments",
        help_text="Links follow-up payment records (refunds, add-ons, etc.) back to the root payment.",
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    adjustments_total_amt = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    currency = models.CharField(max_length=10, default="USD")
    service_address = models.TextField(blank=True)

    stripe_payment_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text="Unique Stripe payment intent ID for this transaction."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Paid"
    )
    payment_type = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} — ${self.amount:.2f} ({self.status})"

    # ============================================================
    # 💰 Helper: compute all totals for this chain
    # ============================================================
    def compute_sections(self):
        root = self if self.parent is None else self.parent
        adjustments = getattr(root, "adjustments", None)

        if not adjustments:
            return (root.amount, Decimal("0.00"), Decimal("0.00"), root.amount)

        add_total = Decimal("0.00")
        cancel_total = Decimal("0.00")

        for adj in adjustments.all():
            if adj.amount >= 0:
                add_total += adj.amount
            else:
                cancel_total += adj.amount

        original_total = root.amount
        net_total = (original_total + add_total + cancel_total).quantize(
            Decimal("0.01")
        )
        return (original_total, add_total, cancel_total, net_total)

    # ============================================================
    # 🧾 Convenience: human-friendly label
    # ============================================================
    @property
    def summary_label(self):
        if self.status == "Refunded" and self.amount < 0:
            pct = (
                abs(self.amount / (self.parent.amount or 1)) * 100
                if self.parent
                else 0
            )
            return f"Refund ({pct:.0f}%) — ${abs(self.amount):.2f}"
        elif self.status == "Adjustment" and self.amount > 0:
            return f"Added Service — ${self.amount:.2f}"
        else:
            return f"{self.status} — ${self.amount:.2f}"

    # ============================================================
    # 📧 Auto-notify on create: refunds, add-ons, cancellations
    # ============================================================
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Send email only when new record created
        if is_new and self.user and self.status in ["Refunded", "Adjustment", "Cancelled"]:
            try:
                subject = f"Tucker & Dale’s — {self.status} Notification"
                message = (
                    f"Hello {self.user.username},\n\n"
                    f"This is a confirmation of a recent {self.status.lower()} "
                    f"related to your booking at:\n\n"
                    f"{self.service_address or '(No address specified)'}\n\n"
                    f"Amount: ${abs(self.amount):.2f}\n"
                    f"Status: {self.status}\n"
                    f"Date: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"Thank you for choosing Tucker & Dale’s Home Services!"
                )

                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [self.user.email],
                    fail_silently=True,
                )
                print(
                    f"📧 Auto-email sent to {self.user.email} for {self.status}")
            except Exception as e:
                print(f"❌ Failed to send {self.status} email: {e}")
