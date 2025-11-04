from django.utils.timezone import now
from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from typing import TYPE_CHECKING
# from scheduling.models import TimeSlot, ServiceCategory, Employee


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
    """
    Represents one booked service line item.
    A booking may have multiple PaymentHistory records
    (initial charge, refund, adjustment, etc.).
    """

    STATUS_CHOICES = [
        ("Booked", "Booked"),
        ("Cancelled", "Cancelled"),
        ("Completed", "Completed"),
    ]

    # Who booked
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True,
    )

    # What / when / where
    service_address = models.CharField(max_length=255)
    date = models.DateField()
    time_slot = models.ForeignKey("TimeSlot", on_delete=models.CASCADE)
    service_category = models.ForeignKey(
        "ServiceCategory", on_delete=models.CASCADE)
    employee = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )

    # Money
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Lifecycle
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Booked")
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    primary_payment_record = models.ForeignKey(
        "billing.PaymentHistory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_bookings_direct",
        help_text="Links this booking to its primary payment record for refunds or adjustments."
    )

    class Meta:
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'} — {self.service_category} on {self.date} {self.time_slot}"

    # -----------------------
    # 🔧 Helpers
    # -----------------------
    @property
    def is_cancelled(self) -> bool:
        return self.status == "Cancelled"

    @property
    def hours_until(self) -> float:
        """Convenience for penalty window checks."""
        return (
            (self.datetime_start - now()).total_seconds() / 3600
            if self.datetime_start
            else (self.date - now().date()).days * 24.0
        )

    @property
    def datetime_start(self):
        """If TimeSlot defines start_time, combine with date."""
        try:
            from datetime import datetime
            return datetime.combine(self.date, self.time_slot.start_time)
        except Exception:
            return None


class JobAssignment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    jobsite_address = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        if not self.jobsite_address:
            self.jobsite_address = self.booking.service_address
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} → {self.jobsite_address} ({self.booking.time_slot})"
