def get_available_employees(customer_address, date, time_slot, service_category):
    """
    Returns employees in a given category who can take this job slot.
    Rules:
    - If already booked in this slot → skip.
    - If no jobs yet that day → check travel time from home.
    - If has adjacent jobs → check travel feasibility (<= 30 min).
    """
    available = []
    employees = Employee.objects.filter(service_category=service_category)

    for emp in employees:
        # Already booked in this slot? skip
        if emp.jobassignment_set.filter(
            booking__date=date, booking__time_slot=time_slot
        ).exists():
            continue

        # Fetch today's jobs for this employee
        todays_jobs = (
            emp.jobassignment_set.filter(booking__date=date)
            .select_related("booking__time_slot")
            .order_by("booking__time_slot__id")
        )

        if not todays_jobs.exists():
            # No jobs yet → use home address
            drive_time = calculate_drive_time(
                emp.home_address, customer_address)
            if drive_time <= 30:
                available.append(emp)
            continue

        feasible = True
        for job in todays_jobs:
            drive_time = calculate_drive_time(
                job.jobsite_address, customer_address)
            if drive_time > 30:
                feasible = False
                break

        if feasible:
            available.append(emp)

    return available
