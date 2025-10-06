from django.utils.timezone import now
from django.db import models
from django.utils import timezone


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
