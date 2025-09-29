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
    name = models.CharField(max_length=255)
    home_address = models.CharField(max_length=255)
    service_category = models.ForeignKey(
        "ServiceCategory", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.service_category.name})"

    def current_location(self, date, time_slot):
        """
        Returns the employee's location for a given date & slot.
        - If booked in this slot → that jobsite.
        - Else if booked earlier that day → last jobsite.
        - Else → home address.
        """
        assignments = (
            self.jobassignment_set.filter(booking__date=date)
            .select_related("booking__time_slot")
            .order_by("booking__time_slot__id")
        )

        # Booked in this slot? → return jobsite
        slot_job = assignments.filter(booking__time_slot=time_slot).first()
        if slot_job:
            return slot_job.jobsite_address

        # Else, get the last job that day
        last_job = assignments.last()
        if last_job:
            return last_job.jobsite_address

        # Default → home address
        return self.home_address


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
