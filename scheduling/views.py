import datetime
from decimal import Decimal
from datetime import datetime as dt

from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token

from scheduling.models import (
    TimeSlot,
    ServiceCategory,
    Employee,
    Cart,
    CartItem,
)
from core.constants import SERVICE_PRICES, SALES_TAX_RATE
from .forms import SearchByDateForm, SearchByTimeSlotForm
from .availability import get_available_employees


# =========================================================
# 🔎 SEARCH VIEWS
# =========================================================
def _get_or_create_cart(request):
    """
    Retrieve or initialize the user's active cart.
    Works for both logged-in users and anonymous sessions.
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        cart = Cart.objects.filter(session_key=session_key).first()
        if not cart:
            cart = Cart.objects.create(session_key=session_key)
            request.session["cart_id"] = cart.id

    return cart


def search_by_date(request):
    """
    Handles searching available employees for a given date and address.
    Displays results grouped by time slot and service category.
    Also provides an initialized Cart object for drag-and-drop additions.
    """
    form = SearchByDateForm(request.GET or None)
    results = None

    if form.is_valid():
        date = form.cleaned_data["date"]
        customer_address = form.cleaned_data["customer_address"]

        # Retrieve all time slots and categories
        slots = TimeSlot.objects.all().order_by("id")
        categories = ServiceCategory.objects.all()

        # Build nested results: { slot -> { category -> [employees] } }
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
            f"✅ DEBUG: Date={date}, Results built for {len(results)} time slots")
    else:
        print(f"❌ DEBUG: Invalid form data: {form.errors}")

    # Always provide a cart instance (for drag-and-drop functionality)
    cart = _get_or_create_cart(request)

    return render(
        request,
        "scheduling/search_by_date.html",
        {
            "form": form,
            "results": results,
            "cart": cart,
            "GOOGLE_MAPS_BROWSER_KEY": settings.GOOGLE_MAPS_BROWSER_KEY,
        },
    )


def search_by_time_slot(request):
    form = SearchByTimeSlotForm(request.GET or None)
    results = None

    if form.is_valid():
        slot = form.cleaned_data["time_slot"]
        customer_address = form.cleaned_data["customer_address"]

        results = {}
        today = datetime.date.today()
        days = [today + datetime.timedelta(days=i) for i in range(28)]
        all_categories = ServiceCategory.objects.all()

        for day in days:
            results[day] = {}
            for category in all_categories:
                results[day][category.name] = get_available_employees(
                    customer_address=customer_address,
                    date=day,
                    time_slot=slot,
                    service_category=category,
                )

        print(
            f"✅ DEBUG: VALID FORM slot={slot} addr={customer_address} results={len(results)}")
    else:
        print(f"❌ DEBUG: INVALID FORM — errors={form.errors}")

    # Pass the current cart to the template
    cart = _get_or_create_cart(request)

    return render(
        request,
        "scheduling/search_by_time_slot.html",
        {
            "form": form,
            "results": results,
            "time_slots": TimeSlot.objects.all(),
            "cart": cart,
            "GOOGLE_MAPS_BROWSER_KEY": settings.GOOGLE_MAPS_BROWSER_KEY,
        },
    )


def choose_search(request):
    return render(request, "scheduling/choose_search.html")


# =========================================================
# 🛒 CART UTILITIES
# =========================================================

def _ensure_session(request):
    """Guarantee that an anonymous user has a session key."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _get_or_create_cart(request):
    """Return the active Cart for this request (user or session)."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    session_key = _ensure_session(request)
    cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart


# =========================================================
# 🧩 CART VIEWS
# =========================================================
@require_POST
def cart_add(request):
    """
    AJAX endpoint called when a pill is dropped into the cart.
    Applies hourly rate and sales tax from core/constants.py
    """
    cart = _get_or_create_cart(request)

    employee_id = request.POST.get("employee_id")
    service_id = request.POST.get("service_category_id")
    slot_id = request.POST.get("time_slot_id")
    date_str = request.POST.get("date")

    if not all([employee_id, service_id, slot_id, date_str]):
        return JsonResponse({"ok": False, "error": "Missing parameters."}, status=400)

    try:
        date_obj = dt.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"ok": False, "error": "Bad date format."}, status=400)

    try:
        employee = Employee.objects.get(pk=employee_id)
        service = ServiceCategory.objects.get(pk=service_id)
        slot = TimeSlot.objects.get(pk=slot_id)
    except (Employee.DoesNotExist, ServiceCategory.DoesNotExist, TimeSlot.DoesNotExist):
        return JsonResponse({"ok": False, "error": "Invalid reference."}, status=404)

    # --------------------------------------------------------
    # 💰 Look up base hourly rate from constants
    # --------------------------------------------------------
    base_rate = Decimal("0.00")
    for key, value in SERVICE_PRICES.items():
        if key.lower() in service.name.lower():
            base_rate = Decimal(str(value))
            break

    # Apply your sales tax multiplier
    tax_multiplier = Decimal("1.00") + Decimal(str(SALES_TAX_RATE))
    unit_price = (base_rate * tax_multiplier).quantize(Decimal("0.01"))

    # --------------------------------------------------------
    # 🧾 Create or update the cart item
    # --------------------------------------------------------
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        employee=employee,
        service_category=service,
        time_slot=slot,
        date=date_obj,
        defaults={"unit_price": unit_price, "quantity": 1},
    )

    if not created:
        item.unit_price = unit_price  # update if changed
        item.save(update_fields=["unit_price"])

    html = render_to_string("scheduling/_cart.html",
                            {"cart": cart}, request=request)
    return JsonResponse({
        "ok": True,
        "html": html,
        "count": cart.items.count(),
        "total": str(cart.total)
    })


@require_POST
def cart_remove(request):
    cart = _get_or_create_cart(request)
    item_id = request.POST.get("item_id")
    try:
        item = cart.items.get(pk=item_id)
    except CartItem.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Not found."}, status=404)
    item.delete()
    html = render_to_string("scheduling/_cart.html",
                            {"cart": cart}, request=request)
    return JsonResponse({"ok": True, "html": html, "count": cart.items.count(), "total": str(cart.total)})


@require_POST
def cart_clear(request):
    cart = _get_or_create_cart(request)
    cart.items.all().delete()
    html = render_to_string("scheduling/_cart.html",
                            {"cart": cart}, request=request)
    return JsonResponse({"ok": True, "html": html, "count": 0, "total": "0.00"})


def cart_detail(request):
    """Optional full-page cart view (non-AJAX)."""
    cart = _get_or_create_cart(request)
    get_token(request)  # ensure CSRF cookie
    return render(request, "scheduling/cart_detail.html", {"cart": cart})
