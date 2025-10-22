from django.utils.timezone import now
from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from typing import TYPE_CHECKING


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class TimeSlot(models.Model):
    label = models.CharField(max_length=20, unique=True)  # e.g., "7:30-9:30"

    def __str__(self):
        return self.label


class Employee(models.Model):
    name = models.CharField(max_length=100)
    home_address = models.CharField(max_length=255)
    service_category = models.ForeignKey(
        "ServiceCategory", on_delete=models.CASCADE
    )

    def __str__(self):
        return self.name

    def current_location(self, date, time_slot):
        """
        Returns the jobsite address if this employee is already assigned
        to a booking at the given date/slot. Otherwise falls back to home.
        """
        assignment = self.jobassignment_set.filter(
            booking__date=date,
            booking__time_slot=time_slot,
        ).first()

        if assignment:
            return assignment.jobsite_address
        return self.home_address

    def next_location(self, date, time_slot):
        """
        Returns the next jobsite address *after* this slot on the same day.
        If none, returns None.
        """
        next_assignment = (
            self.jobassignment_set.filter(
                booking__date=date,
                booking__time_slot__id__gt=time_slot.id,  # any later slot that day
            )
            .order_by("booking__time_slot__id")
            .first()
        )

        if next_assignment:
            return next_assignment.jobsite_address
        return None


class Booking(models.Model):
    customer_name = models.CharField(max_length=255)
    customer_address = models.CharField(max_length=255)
    date = models.DateField()
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    service_category = models.ForeignKey(
        ServiceCategory, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.customer_name} ({self.service_category} on {self.date} at {self.time_slot})"


class JobAssignment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    jobsite_address = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        if not self.jobsite_address:
            self.jobsite_address = self.booking.customer_address
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} → {self.jobsite_address} ({self.booking.time_slot})"


# class CartManager(models.Manager):
#     """
#     Centralized helper to fetch or create a cart
#     for the current request (user or anonymous session).
#     """

#     def get_for_request(self, request):
#         # Ensure session exists
#         if not request.session.session_key:
#             request.session.save()

#         if request.user.is_authenticated:
#             cart, _ = self.get_or_create(user=request.user)
#         else:
#             cart, _ = self.get_or_create(
#                 session_key=request.session.session_key)

#         return cart


# class Cart(models.Model):
#     """
#     Represents a booking or shopping cart for a single customer session.
#     Each cart is tied to either a logged-in user or an anonymous session_key,
#     and optionally to a normalized address_key for address-based isolation.
#     """

#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         null=True,
#         blank=True,
#         on_delete=models.CASCADE,
#         related_name="carts",
#     )

#     session_key = models.CharField(
#         max_length=40,
#         null=True,
#         blank=True,
#         db_index=True,
#         help_text="Anonymous session identifier for guests.",
#     )

#     address_key = models.CharField(
#         max_length=255,
#         blank=True,
#         null=True,
#         db_index=True,
#         help_text="Normalized address string for session-level cart isolation.",
#     )

#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)

#     if TYPE_CHECKING:
#         from scheduling.models import CartItem
#         items: "models.Manager[CartItem]"

#     class Meta:
#         indexes = [
#             models.Index(fields=["session_key"]),
#             models.Index(fields=["user"]),
#             models.Index(fields=["address_key"]),
#         ]
#         ordering = ["-updated_at"]

#     def __str__(self):
#         owner = self.user or self.session_key or "anonymous"
#         return f"Cart<{owner}>"

#     # ----------------------------------------------------
#     # 💲 Computed Totals
#     # ----------------------------------------------------
#     @property
#     def subtotal(self) -> Decimal:
#         """Sum of all item subtotals (PRE-TAX)."""
#         total = sum(
#             (item.subtotal for item in self.items.all()),
#             Decimal("0.00"),
#         )
#         return total.quantize(Decimal("0.01"))

#     @property
#     def tax(self) -> Decimal:
#         """Tax computed once on subtotal."""
#         from core.constants import SALES_TAX_RATE
#         tax_rate = Decimal(str(SALES_TAX_RATE))
#         return (self.subtotal * tax_rate).quantize(Decimal("0.01"))

#     @property
#     def total(self) -> Decimal:
#         """Grand total = subtotal + tax."""
#         return (self.subtotal + self.tax).quantize(Decimal("0.01"))

#     # ----------------------------------------------------
#     # 🧹 Utilities
#     # ----------------------------------------------------
#     def clear(self):
#         """Remove all items from this cart."""
#         self.items.all().delete()

#     @property
#     def item_count(self) -> int:
#         """Convenience property for navbar badge count."""
#         return self.items.count()

#     def has_items(self) -> bool:
#         """Return True if the cart has any items."""
#         return self.items.exists()


# class CartItem(models.Model):
#     """
#     One service assignment the customer intends to book.
#     Uniqueness prevents duplicate same-slot/employee entries in the same cart.
#     """
#     cart = models.ForeignKey(
#         "scheduling.Cart",
#         on_delete=models.CASCADE,
#         related_name="items",          # enables cart.items.all()
#     )
#     service_category = models.ForeignKey(
#         "scheduling.ServiceCategory",
#         on_delete=models.PROTECT,      # prevent deletion if still referenced
#     )
#     time_slot = models.ForeignKey(
#         "scheduling.TimeSlot",
#         on_delete=models.PROTECT,
#     )
#     employee = models.ForeignKey(
#         "scheduling.Employee",
#         on_delete=models.PROTECT,
#     )
#     date = models.DateField()

#     # --- Pricing fields ---
#     unit_price = models.DecimalField(
#         max_digits=8,
#         decimal_places=2,
#         default=0,
#         help_text="Stored as PRE-TAX price per 2-hour service block.",
#     )
#     quantity = models.PositiveIntegerField(default=1)

#     # --- Metadata ---
#     created_at = models.DateTimeField(default=timezone.now)

#     class Meta:
#         unique_together = (
#             ("cart", "service_category", "time_slot", "date", "employee"),
#         )

#     def __str__(self):
#         return f"{self.service_category} | {self.date} {self.time_slot} | {self.employee}"

#     @property
#     def subtotal(self) -> Decimal:
#         return (self.unit_price * self.quantity).quantize(Decimal("0.01"))
