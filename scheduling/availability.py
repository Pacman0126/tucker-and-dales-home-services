import requests
import logging
from django.conf import settings
from .models import Employee

logger = logging.getLogger(__name__)

# -----------------------------------------------------
# 🔹 1. Helper – robust server-side Distance Matrix call
# -----------------------------------------------------


def calculate_drive_time(addr1, addr2):
    """
    Uses Google Distance Matrix API to calculate drive time in minutes.
    Uses the secure SERVER key (backend only).
    Returns an integer (minutes) or None if the API call fails.
    """

    print("🔑 Using key prefix:", settings.GOOGLE_MAPS_SERVER_KEY[:10])
    if not addr1 or not addr2:
        logger.warning("Drive time skipped: missing origin or destination.")
        return None

    api_key = getattr(settings, "GOOGLE_MAPS_SERVER_KEY", None)
    if not api_key:
        logger.error("GOOGLE_MAPS_SERVER_KEY missing in settings.")
        return None

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": addr1,
        "destinations": addr2,
        "mode": "driving",
        "key": api_key,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        # Handle known error statuses
        status = data.get("status")
        if status == "REQUEST_DENIED":
            err = data.get("error_message", "(no message)")
            logger.error(f"❌ Google API denied request: {err}")
            return None
        if status != "OK":
            logger.warning(f" Distance Matrix returned non-OK: {status}")
            return None

        element = data["rows"][0]["elements"][0]
        if element.get("status") == "OK":
            seconds = element["duration"]["value"]
            return round(seconds / 60)
        else:
            logger.warning(f"Element status not OK: {element.get('status')}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f" Drive time network error: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected drive time error: {e}")
        return None


# -----------------------------------------------------
# 🔹 2. Main availability logic
# -----------------------------------------------------
def get_available_employees(customer_address, date, time_slot, service_category):
    """
    Returns employees in a given category who can take this job slot.
    Always computes drive time, even for idle employees.
    """
    employees = Employee.objects.filter(service_category=service_category)
    available = []

    logger.info(
        f"🔎 Checking {service_category} availability for {date} [{time_slot.label}]"
    )

    for emp in employees:
        # Skip if already booked this slot
        if emp.jobassignment_set.filter(
            booking__date=date, booking__time_slot=time_slot
        ).exists():
            continue

        # --- Determine origin and next destination ---
        start_loc = emp.current_location(date, time_slot)
        end_loc = emp.next_location(date, time_slot)

        # If no current location, fall back to employee home address
        route_origin = start_loc or emp.home_address or "Dallas, TX"

        # --- Compute drive times ---
        drive_time_to_customer = calculate_drive_time(
            route_origin, customer_address)
        drive_time_to_next = (
            calculate_drive_time(customer_address, end_loc)
            if end_loc else None
        )

        # --- Feasibility (≤ 30 minutes each way) ---
        feasible = True
        if drive_time_to_customer is None or drive_time_to_customer > 30:
            feasible = False
        if drive_time_to_next is not None and drive_time_to_next > 30:
            feasible = False

        # --- Store for display and visualization ---
        emp.drive_time = (
            f"{drive_time_to_customer} min" if drive_time_to_customer is not None else "N/A"
        )
        emp.route_origin = route_origin  # used by template “View Routes” modal

        # --- Collect if feasible ---
        if feasible:
            available.append(emp)

    # Optional: concise table in logs
    if available:
        logger.info("Available employees:")
        for e in available:
            logger.info(
                f"  - {e.name:<25} | {e.drive_time:<6} | {e.route_origin}")
    else:
        logger.info("No employees available for this slot.")

    # Compact table summary
    if available:
        logger.info(" Available employees:")
        for e in available:
            logger.info(f"   - {e.name:<25} | {e.drive_time}")
    else:
        logger.info(" No employees available in this category/time slot.")

    return available
