
import datetime
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from billing.utils import _get_or_create_cart
from billing.models import Cart
from scheduling.utils import get_locked_address, lock_service_address
from .models import Booking

from .models import (
    Employee,
)

from .forms import SearchByDateForm, SearchByTimeSlotForm
from .models import TimeSlot, ServiceCategory
from .availability import get_available_employees


# ============================================================
# 🔹 Search by Date
# ============================================================


def unlock_address(request):
    """
    Clears the current cart and unlocks the service address for both
    anonymous and authenticated users.
    Returns JSON if called via AJAX; fallback redirect otherwise.
    """
    if request.method == "POST":
        request.session.pop("service_address", None)
        request.session["address_locked"] = False

        # Clear related carts
        try:
            if request.user.is_authenticated:
                Cart.objects.filter(user=request.user).delete()
            elif request.session.session_key:
                Cart.objects.filter(
                    session_key=request.session.session_key).delete()
        except Exception as e:
            print(f"⚠️ Cart cleanup failed during address unlock: {e}")

        request.session.modified = True

        # AJAX response
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "message":
                                 "Cart cleared and address unlocked."}
                                )

        # Fallback redirect
        messages.info(
            request, "✅ Cart cleared — you can now book for a new address.")
        return redirect("scheduling:search_by_date")

    return JsonResponse({"ok": False, "error": "Invalid request method."},
                        status=405)


def search_by_date(request):
    """
    Handles searching available employees for a given date and service address.
    - Address lock persists across search modes.
    - Falls back to locked session address if field omitted.
    """

    # --- 1️⃣ Get session lock info ---
    locked_address, address_locked = get_locked_address(request)
    form = SearchByDateForm(request.GET or None,
                            user=request.user, locked_address=locked_address)

    results = None

    # --- 3️⃣ If valid, perform search ---
    if form.is_valid():
        date = form.cleaned_data["date"]
        customer_address = (
            form.cleaned_data.get("customer_address", "") or locked_address
        ).strip()

        # --- Lock address if not already locked ---
        if not locked_address and customer_address:
            lock_service_address(request, customer_address)
            locked_address = customer_address
            address_locked = True
            messages.info(
                request,
                f"Service address '{locked_address}' locked for this session."
            )

        # --- Enforce lock ---
        if (locked_address and customer_address.lower() !=
                locked_address.lower()):
            messages.warning(
                request, (
                    "Service address is locked for this session: "
                    f"{locked_address}. "
                    "Start a new booking session to change it."
                )
            )
            customer_address = locked_address

        # --- Build grid of available employees (slots × category) ---
        slots = TimeSlot.objects.all().order_by("id")
        categories = ServiceCategory.objects.all()

        results = {
            slot: {
                category: get_available_employees(
                    customer_address=customer_address,
                    date=date,
                    time_slot=slot,
                    service_category=category,
                )
                for category in categories
            }
            for slot in slots
        }

        print(
            (f"✅ DEBUG: SearchByDate → Date={date}, "
             f"Address={locked_address}, Results={len(results)} slots")
        )

    else:
        print(f"❌ DEBUG: Invalid SearchByDateForm → {form.errors}")

    # --- 4️⃣ Render context ---
    cart = _get_or_create_cart(request)
    context = {
        "form": form,
        "results": results,
        "cart": cart,
        "navbar_mode": "booking",
        "GOOGLE_MAPS_BROWSER_KEY": settings.GOOGLE_MAPS_BROWSER_KEY,
        "address_locked": address_locked,
        "locked_address": locked_address,
    }

    return render(request, "scheduling/search_by_date.html", context)


def search_by_time_slot(request):
    """
    Allows searching by time slot across a 4-week window, one week at a time.

    Why this version:
    - preserves the 28-day search horizon
    - computes only 7 days per request in production
    - keeps existing locked-address behavior
    - keeps existing get_available_employees() routing logic unchanged
    - adds simple week pagination via ?week=1..4
    """
    # --- 1️⃣ Retrieve locked service address (if any) ---
    locked_address, address_locked = get_locked_address(request)

    form = SearchByTimeSlotForm(
        request.GET or None,
        user=request.user,
        locked_address=locked_address,
    )

    print(f"DEBUG FORM DATA: {form.data}")

    results = None

    # --- 2️⃣ Pagination / batching config ---
    total_weeks = 4
    days_per_week = 7

    try:
        selected_week = int(request.GET.get("week", 1))
    except (TypeError, ValueError):
        selected_week = 1

    selected_week = max(1, min(selected_week, total_weeks))

    # --- 3️⃣ Process search if valid ---
    if form.is_valid():
        slot = form.cleaned_data["time_slot"]
        customer_address = (
            form.cleaned_data.get("customer_address", "") or locked_address
        ).strip()

        # --- Lock service address if not already locked ---
        if not locked_address and customer_address:
            lock_service_address(request, customer_address)
            locked_address = customer_address
            address_locked = True
            messages.info(
                request,
                f"Service address '{locked_address}' locked for this session."
            )

        # --- Enforce locked address ---
        if (locked_address and customer_address.lower() !=
                locked_address.lower()):
            messages.warning(
                request,
                (f"Service address is locked "
                 f"for this session: {locked_address}. "
                 "Start a new booking session to change it.")
            )
            customer_address = locked_address

        # - Build only the selected 7-day slice out of the full 28-day window
        today = datetime.date.today()
        start_offset = (selected_week - 1) * days_per_week
        end_offset = start_offset + days_per_week

        days = [
            today + datetime.timedelta(days=i)
            for i in range(start_offset, end_offset)
        ]

        categories = ServiceCategory.objects.all()

        results = {
            day: {
                category.name: [
                    {
                        "id": emp.id,
                        "name": emp.name,
                        "home_address": emp.home_address,
                        "drive_time": getattr(emp, "drive_time", None),
                        "route_origin": getattr(emp, "route_origin", None),
                        "service_category_id": category.id,
                        "time_slot_id": slot.id,
                        "date": day.strftime("%Y-%m-%d"),
                    }
                    for emp in get_available_employees(
                        customer_address=customer_address,
                        date=day,
                        time_slot=slot,
                        service_category=category,
                    )
                ]
                for category in categories
            }
            for day in days
        }

        print(
            "✅ DEBUG: SearchByTimeSlot → "
            f"Slot={slot}, Address={locked_address}, "
            f"Week={selected_week}/{total_weeks}, Days={len(results)}"
        )
    else:
        print(f"❌ DEBUG: Invalid SearchByTimeSlotForm → {form.errors}")

    # --- 4️⃣ Build week navigation metadata for template ---
    today = datetime.date.today()
    week_ranges = []

    for week_num in range(1, total_weeks + 1):
        week_start = today + \
            datetime.timedelta(days=(week_num - 1) * days_per_week)
        week_end = week_start + datetime.timedelta(days=days_per_week - 1)

        week_ranges.append(
            {
                "number": week_num,
                "label": f"Week {week_num}",
                "start": week_start,
                "end": week_end,
                "is_active": week_num == selected_week,
            }
        )

    active_week = next(
        (week for week in week_ranges if week["number"] == selected_week),
        None,
    )

    # --- 5️⃣ Render template ---
    cart = _get_or_create_cart(request)

    context = {
        "form": form,
        "results": results,
        "cart": cart,
        "time_slots": TimeSlot.objects.all(),
        "navbar_mode": "booking",
        "GOOGLE_MAPS_BROWSER_KEY": settings.GOOGLE_MAPS_BROWSER_KEY,
        "address_locked": address_locked,
        "locked_address": locked_address,
        "selected_week": selected_week,
        "total_weeks": total_weeks,
        "week_ranges": week_ranges,
        "active_week": active_week,
    }
    return render(request, "scheduling/search_by_time_slot.html", context)


def staff_required(user):
    return user.is_authenticated and user.is_staff and not user.is_superuser


# @login_required
# @user_passes_test(staff_required)
# def staff_dashboard(request):
#     """
#     Minimal staff-only dashboard.

#     Because Employee currently has no direct link to auth.User,
#     this resolves the matching Employee record by comparing:
#     - user's full name
#     - username

#     Shows upcoming booked jobs assigned to that employee, plus
#     customer name and phone (if a CustomerProfile exists).
#     """
#     today = timezone.localdate()

#     full_name = (request.user.get_full_name() or "").strip()
#     username = (request.user.username or "").strip()

#     employee = None

#     if full_name and username:
#         employee = Employee.objects.filter(
#             Q(name__iexact=full_name) | Q(name__iexact=username)
#         ).first()
#     elif full_name:
#         employee = Employee.objects.filter(name__iexact=full_name).first()
#     elif username:
#         employee = Employee.objects.filter(name__iexact=username).first()

#     bookings = Booking.objects.none()

#     if employee:
#         bookings = (
#             Booking.objects.select_related(
#                 "service_category",
#                 "time_slot",
#                 "employee",
#                 "user",
#                 "user__customer_profile",
#             )
#             .filter(
#                 employee=employee,
#                 date__gte=today,
#                 status="Booked",
#             )
#             .order_by("date", "time_slot__id", "created_at")
#         )
#     else:
#         messages.warning(
#             request,
#             "No Employee record matches this staff login. "
#             "For this minimal staff dashboard, set Employee.name to match "
#             "the staff user's full name or username."
#         )

#     return render(
#         request,
#         "scheduling/staff_dashboard.html",
#         {
#             "employee": employee,
#             "bookings": bookings,
#             "today": today,
#         },
#     )
@login_required
def staff_dashboard(request):
    """
    Minimal staff-only dashboard.

    Because Employee currently has no direct link to auth.User,
    this resolves the matching Employee record by comparing:
    - user's full name
    - username

    Non-staff users are redirected safely instead of being sent into
    a login redirect loop.
    """
    if not request.user.is_staff or request.user.is_superuser:
        messages.error(
            request,
            "You do not have permission to access the staff dashboard."
        )
        return redirect("core:home")

    today = timezone.localdate()

    full_name = (request.user.get_full_name() or "").strip()
    username = (request.user.username or "").strip()

    employee = None

    if full_name and username:
        employee = Employee.objects.filter(
            Q(name__iexact=full_name) | Q(name__iexact=username)
        ).first()
    elif full_name:
        employee = Employee.objects.filter(name__iexact=full_name).first()
    elif username:
        employee = Employee.objects.filter(name__iexact=username).first()

    bookings = Booking.objects.none()

    if employee:
        bookings = (
            Booking.objects.select_related(
                "service_category",
                "time_slot",
                "employee",
                "user",
                "user__customer_profile",
            )
            .filter(
                employee=employee,
                date__gte=today,
                status="Booked",
            )
            .order_by("date", "time_slot__id", "created_at")
        )
    else:
        messages.warning(
            request,
            "No Employee record matches this staff login. "
            "For this minimal staff dashboard, set Employee.name to match "
            "the staff user's full name or username."
        )

    return render(
        request,
        "scheduling/staff_dashboard.html",
        {
            "employee": employee,
            "bookings": bookings,
            "today": today,
        },
    )
