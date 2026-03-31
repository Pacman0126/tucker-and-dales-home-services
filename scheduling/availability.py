import logging
from decimal import Decimal
from urllib.parse import quote_plus

import requests
from django.conf import settings
from django.core.cache import cache

from .models import Booking, Employee, JobAssignment

logger = logging.getLogger(__name__)

# -----------------------------------------------------
# 🔹 0. Tunables
# -----------------------------------------------------
DRIVE_TIME_CACHE_TTL = 60 * 60 * 6  # 6 hours
DEFAULT_FALLBACK_CITY = "Dallas, TX"
MAX_FEASIBLE_DRIVE_MINUTES = 30


# -----------------------------------------------------
# 🔹 1. Helpers
# -----------------------------------------------------
def _normalize_addr(value):
    return (value or "").strip()


def _drive_cache_key(addr1, addr2):
    a1 = _normalize_addr(addr1).lower()
    a2 = _normalize_addr(addr2).lower()
    return f"drive_time:{quote_plus(a1)}:{quote_plus(a2)}"


# -----------------------------------------------------
# 🔹 2. Robust server-side Distance Matrix call
# -----------------------------------------------------
def calculate_drive_time(addr1, addr2):
    """
    Uses Google Distance Matrix API to calculate drive time in minutes.
    Uses the secure SERVER key (backend only).
    Returns an integer (minutes) or None if the API call fails.

    Optimizations:
    - skips empty addresses early
    - caches repeated origin/destination lookups
    """
    addr1 = _normalize_addr(addr1)
    addr2 = _normalize_addr(addr2)

    if not addr1 or not addr2:
        logger.warning("Drive time skipped: missing origin or destination.")
        return None

    cache_key = _drive_cache_key(addr1, addr2)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    api_key = getattr(settings, "GOOGLE_MAPS_SERVER_KEY", None)
    if not api_key:
        logger.error("GOOGLE_MAPS_SERVER_KEY missing in settings.")
        return None

    print("🔑 Using key prefix:", settings.GOOGLE_MAPS_SERVER_KEY[:10])

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

        status = data.get("status")
        if status == "REQUEST_DENIED":
            err = data.get("error_message", "(no message)")
            logger.error(f"❌ Google API denied request: {err}")
            return None

        if status != "OK":
            logger.warning(f"Distance Matrix returned non-OK: {status}")
            return None

        rows = data.get("rows") or []
        if not rows or not rows[0].get("elements"):
            logger.warning("Distance Matrix returned empty rows/elements.")
            return None

        element = rows[0]["elements"][0]
        if element.get("status") == "OK":
            seconds = element["duration"]["value"]
            minutes = round(Decimal(seconds) / Decimal("60"))
            cache.set(cache_key, int(minutes), DRIVE_TIME_CACHE_TTL)
            return int(minutes)

        logger.warning(f"Element status not OK: {element.get('status')}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Drive time network error: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected drive time error: {e}")
        return None


# -----------------------------------------------------
# 🔹 3. Main availability logic
# -----------------------------------------------------
def get_available_employees(customer_address, date, time_slot, service_category):
    """
    Returns employees in a given category who can take this job slot.
    Always computes drive time, even for idle employees.

    Optimizations:
    - precomputes employee IDs already blocked for this date/slot
    - preloads all same-day assignments once
    - attaches request-local current/next location caches to employees
    - keeps existing current_location / next_location API intact
    - caches Google route calls

    Important booking integrity rule:
    - An employee is NOT available if they already have:
      1) a JobAssignment for this exact date/slot, OR
      2) a live Booking for this exact date/slot

    This prevents already-paid slots from reappearing in fresh searches.
    """
    customer_address = _normalize_addr(customer_address)

    employees = list(
        Employee.objects.filter(service_category=service_category)
    )
    available = []

    logger.info(
        f"🔎 Checking {service_category} availability for {date} [{time_slot.label}]"
    )

    if not employees:
        logger.info("No employees found for this service category.")
        return available

    employee_ids = [emp.id for emp in employees]

    # -------------------------------------------------
    # 1) Precompute employees already blocked in this exact slot
    # -------------------------------------------------
    # Source A: employees already assigned to a booking in this slot
    booked_employee_ids = set(
        JobAssignment.objects.filter(
            employee_id__in=employee_ids,
            booking__date=date,
            booking__time_slot=time_slot,
        ).values_list("employee_id", flat=True)
    )

    # Source B: employees already sold/booked in this slot, even if a
    # JobAssignment record has not yet been created.
    booked_employee_ids.update(
        Booking.objects.filter(
            employee_id__in=employee_ids,
            date=date,
            time_slot=time_slot,
        )
        .exclude(status__iexact="Cancelled")
        .values_list("employee_id", flat=True)
    )

    # -------------------------------------------------
    # 2) Preload all assignments for these employees on this date
    # -------------------------------------------------
    assignments = list(
        JobAssignment.objects.select_related("booking", "booking__time_slot")
        .filter(
            employee_id__in=employee_ids,
            booking__date=date,
        )
        .order_by("employee_id", "booking__time_slot__id")
    )

    assignments_by_employee = {}
    for assignment in assignments:
        assignments_by_employee.setdefault(
            assignment.employee_id, []).append(assignment)

    # -------------------------------------------------
    # 3) Attach per-employee caches so model methods avoid DB hits
    # -------------------------------------------------
    for emp in employees:
        emp_assignments = assignments_by_employee.get(emp.id, [])

        # current location for the exact slot
        current_loc = _normalize_addr(
            emp.home_address) or DEFAULT_FALLBACK_CITY
        for assignment in emp_assignments:
            if assignment.booking.time_slot_id == time_slot.id:
                current_loc = _normalize_addr(assignment.jobsite_address)
                break

        # next location after the slot
        next_loc = None
        for assignment in emp_assignments:
            if assignment.booking.time_slot_id > time_slot.id:
                next_loc = _normalize_addr(assignment.jobsite_address)
                break

        emp._current_location_cache = {
            (date, time_slot.id): current_loc or DEFAULT_FALLBACK_CITY
        }
        emp._next_location_cache = {
            (date, time_slot.id): next_loc
        }

    # -------------------------------------------------
    # 4) Main employee loop
    # -------------------------------------------------
    for emp in employees:
        # Skip if already booked/blocked for this exact slot
        if emp.id in booked_employee_ids:
            continue

        # Uses cache-aware model methods if present
        start_loc = emp.current_location(date, time_slot)
        end_loc = emp.next_location(date, time_slot)

        route_origin = (
            _normalize_addr(start_loc)
            or _normalize_addr(emp.home_address)
            or DEFAULT_FALLBACK_CITY
        )

        drive_time_to_customer = calculate_drive_time(
            route_origin, customer_address
        )
        drive_time_to_next = (
            calculate_drive_time(customer_address, end_loc)
            if _normalize_addr(end_loc)
            else None
        )

        feasible = True
        if (
            drive_time_to_customer is None
            or drive_time_to_customer > MAX_FEASIBLE_DRIVE_MINUTES
        ):
            feasible = False
        if (
            drive_time_to_next is not None
            and drive_time_to_next > MAX_FEASIBLE_DRIVE_MINUTES
        ):
            feasible = False

        emp.drive_time = (
            f"{drive_time_to_customer} min"
            if drive_time_to_customer is not None
            else "N/A"
        )
        emp.route_origin = route_origin  # used by template “View Routes” modal

        if feasible:
            available.append(emp)

    # -------------------------------------------------
    # 5) Logging
    # -------------------------------------------------
    if available:
        logger.info("Available employees:")
        for e in available:
            logger.info(
                f"  - {e.name:<25} | {e.drive_time:<6} | {e.route_origin}"
            )
    else:
        logger.info("No employees available for this slot.")

    if available:
        logger.info("Available employees:")
        for e in available:
            logger.info(f"   - {e.name:<25} | {e.drive_time}")
    else:
        logger.info("No employees available in this category/time slot.")

    return available
