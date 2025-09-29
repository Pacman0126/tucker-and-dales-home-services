from django.conf import settings
from .models import Employee
from datetime import timedelta

# 🔹 Stub for Google Maps API (replace later)


def calculate_drive_time(addr1, addr2):
    """
    Placeholder for driving time logic.
    Currently hard-coded to 20 minutes.
    Replace with Google Maps Distance Matrix API call later.
    """
    return 20  # minutes


def get_available_employees(customer_address, date, time_slot, service_category):
    """
    Returns employees in a given category who can take this job slot.

    Rules:
    - If already booked in this slot → skip.
    - If no jobs yet that day → check travel time from home.
    - If has jobs that day → check travel feasibility (<= 30 min for ALL jobs).
    """
    available = []
    employees = Employee.objects.filter(service_category=service_category)

    for emp in employees:
        # Already booked in this slot? → skip
        if emp.jobassignment_set.filter(
            booking__date=date, booking__time_slot=time_slot
        ).exists():
            continue

        # Gather all of employee's jobs today
        todays_jobs = (
            emp.jobassignment_set.filter(booking__date=date)
            .select_related("booking__time_slot")
            .order_by("booking__time_slot__id")
        )

        if not todays_jobs.exists():
            # No jobs yet today → start from home
            if calculate_drive_time(emp.home_address, customer_address) <= 30:
                available.append(emp)
            continue

        # Employee has jobs today → must be within 30 min of *all* jobs
        feasible = all(
            calculate_drive_time(job.jobsite_address, customer_address) <= 30
            for job in todays_jobs
        )

        if feasible:
            available.append(emp)

    return available
