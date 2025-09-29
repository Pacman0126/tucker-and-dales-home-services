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
        ServiceCategory, on_delete=models.CASCADE)

    def current_location(self, date, slot):
        """
        Returns the employee's address for a given date and timeslot.
        - If no jobs that day yet → home address
        - Else → last jobsite of the day before or at this slot
        """
        # All assignments for this employee on that day
        assignments = (
            self.jobassignment_set
            .filter(booking__date=date)
            .select_related("booking__time_slot")
            .order_by("booking__time_slot__id")
        )

        if not assignments.exists():
            return self.home_address

        # Find if they have a booking at or before this slot
        for a in assignments:
            if a.booking.time_slot.id <= slot.id:
                last_job = a
            else:
                break

        return last_job.jobsite_address if "last_job" in locals() else self.home_address


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
