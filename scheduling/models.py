from django.utils.timezone import now
from django.db import models


class Employee(models.Model):
    name = models.CharField(max_length=100)
    home_address = models.CharField(max_length=255)
    service_category = models.ForeignKey(
        "ServiceCategory", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.service_category})"

    def current_location(self, date, time_slot):
        """
        Returns the employee's jobsite address if booked at that date+slot,
        otherwise falls back to home address.
        """
        assignment = self.jobassignment_set.filter(
            booking__date=date,
            booking__time_slot=time_slot
        ).first()
        if assignment:
            return assignment.jobsite_address
        return self.home_address


class TimeSlot(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()

    def __str__(self):
        return f"{self.start.strftime('%Y-%m-%d %H:%M')} – {self.end.strftime('%H:%M')}"


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Booking(models.Model):
    customer_name = models.CharField(max_length=200)
    customer_address = models.CharField(max_length=255)
    service_category = models.ForeignKey(
        ServiceCategory, on_delete=models.CASCADE)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    employees = models.ManyToManyField("Employee", through="JobAssignment")

    def __str__(self):
        return f"{self.service_category} @ {self.customer_address} ({self.time_slot})"


class JobAssignment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    jobsite_address = models.CharField(max_length=255, blank=True)

    class Meta:
        # Prevents duplicate entries for the same employee & booking
        unique_together = ("employee", "booking")

    def save(self, *args, **kwargs):
        # Default jobsite address is the booking's customer address
        if not self.jobsite_address:
            self.jobsite_address = self.booking.customer_address
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} → {self.jobsite_address} ({self.booking.time_slot})"
