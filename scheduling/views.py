from decimal import Decimal
import datetime
from datetime import datetime as dt
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token

from billing.utils import _get_or_create_cart

from billing.constants import SERVICE_PRICES, SALES_TAX_RATE


from customers.models import CustomerProfile
from .models import (
    Employee,
)

from billing.models import Cart

from .forms import SearchByDateForm, SearchByTimeSlotForm
from .models import TimeSlot, ServiceCategory
from .availability import get_available_employees

from scheduling.forms import SearchByTimeSlotForm, SearchByDateForm
from scheduling.models import TimeSlot, ServiceCategory

from scheduling.utils import get_locked_address, lock_service_address

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
            return JsonResponse({"ok": True, "message": "Cart cleared and address unlocked."})

        # Fallback redirect
        messages.info(
            request, "✅ Cart cleared — you can now book for a new address.")
        return redirect("scheduling:search_by_date")

    return JsonResponse({"ok": False, "error": "Invalid request method."}, status=405)


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
        if locked_address and customer_address.lower() != locked_address.lower():
            messages.warning(
                request,
                f"Service address is locked for this session: {locked_address}. "
                "Start a new booking session to change it."
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
            f"✅ DEBUG: SearchByDate → Date={date}, Address={locked_address}, Results={len(results)} slots")

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
    Allows searching by time slot across the next 28 days.
    - Respects and enforces locked service address.
    - Automatically falls back to locked session address if field is missing.
    """

    # --- 1️⃣ Retrieve locked service address (if any) ---
    locked_address, address_locked = get_locked_address(request)
    form = SearchByTimeSlotForm(
        request.GET or None, user=request.user, locked_address=locked_address)

    print(f"🔍 DEBUG FORM DATA: {form.data}")
    results = None

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
        if locked_address and customer_address.lower() != locked_address.lower():
            messages.warning(
                request,
                f"Service address is locked for this session: {locked_address}. "
                "Start a new booking session to change it."
            )
            customer_address = locked_address

        # --- Build 28-day × category grid ---
        today = datetime.date.today()
        days = [today + datetime.timedelta(days=i) for i in range(28)]
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
            f"✅ DEBUG: SearchByTimeSlot → Slot={slot}, Address={locked_address}, Days={len(results)}")

    else:
        print(f"❌ DEBUG: Invalid SearchByTimeSlotForm → {form.errors}")

    # --- 4️⃣ Render template ---
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
    }

    return render(request, "scheduling/search_by_time_slot.html", context)
