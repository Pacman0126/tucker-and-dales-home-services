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
    - Skip if already booked.
    - Feasible if travel time from current_location ≤ 30 minutes
      AND (if applicable) travel time to next_location ≤ 30 minutes.
    """
    available = []
    employees = Employee.objects.filter(service_category=service_category)

    for emp in employees:
        # Already booked in this slot? skip
        if emp.jobassignment_set.filter(
            booking__date=date, booking__time_slot=time_slot
        ).exists():
            continue

        # Where are they now? Where are they going next?
        start_loc = emp.current_location(date, time_slot)
        end_loc = emp.next_location(date, time_slot)

        feasible = True
        if calculate_drive_time(start_loc, customer_address) > 30:
            feasible = False
        if end_loc and calculate_drive_time(customer_address, end_loc) > 30:
            feasible = False

        if feasible:
            available.append(emp)

    return available
