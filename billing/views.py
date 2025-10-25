"""
billing/views.py
Handles checkout, Stripe integration, payment tracking, and admin management.
"""
import datetime
from datetime import datetime as dt
import json
from decimal import Decimal
import stripe

from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from customers.models import RegisteredCustomer
from scheduling.models import Employee, TimeSlot, ServiceCategory
from .utils import _get_or_create_cart, get_service_address, lock_service_address, normalize_address, get_active_cart_for_request
from .models import Payment
from .constants import SERVICE_PRICES, SALES_TAX_RATE
from .forms import CheckoutForm
from .models import Cart, CartItem, CartManager
# ----------------------------------------------------------------------
# ⚙️ Stripe Setup
# ----------------------------------------------------------------------
stripe.api_key = settings.STRIPE_SECRET_KEY

# ----------------------------------------------------------------------
# 🏁 Simple Checkout Page (called by navbar burger)
# ----------------------------------------------------------------------


@login_required
def checkout(request):
    """
    Render the checkout page using the *active* cart pinned in the session (cart_id).
    Never silently switches the cart/address_key.
    """
    cart = get_active_cart_for_request(request, create_if_missing=False)

    if not cart or not cart.items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("scheduling:search_by_date")

    context = {
        "cart": cart,
        "selected_services": cart.items.all(),
        "hours": 0,  # if you compute hours elsewhere, keep that logic
        "subtotal": cart.subtotal,
        "tax": cart.tax,
        "total": cart.total,
    }
    return render(request, "billing/checkout.html", context)


# ----------------------------------------------------------------------
# 🧾 Checkout Summary (pre-Stripe)
# ----------------------------------------------------------------------
@login_required
def checkout_summary(request):
    """
    Displays the cart summary before payment.
    Uses the active cart pinned in the session (cart_id),
    ensuring address and billing details are consistent.
    """
    from billing.utils import get_active_cart_for_request, get_service_address
    from customers.models import RegisteredCustomer
    from .forms import CheckoutForm

    # --- 1️⃣ Retrieve the active cart (do NOT auto-create) ---
    cart = get_active_cart_for_request(request, create_if_missing=False)
    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("scheduling:search_by_date")

    # --- 2️⃣ Retrieve service address from session ---
    service_address = get_service_address(request)

    # --- 3️⃣ Retrieve or preload user billing address ---
    billing_address_str = request.session.get("billing_address", "")
    rc = None
    try:
        rc = RegisteredCustomer.objects.get(user=request.user)
        if not billing_address_str and rc.has_valid_billing_address():
            billing_address_str = rc.full_billing_address
            request.session["billing_address"] = billing_address_str
            request.session.modified = True
    except RegisteredCustomer.DoesNotExist:
        # 🚦 redirect to complete profile if missing
        messages.info(request, "Please complete your profile before checkout.")
        request.session["next_after_profile"] = "billing:checkout"
        request.session["checkout_pending"] = True
        request.session.modified = True
        return redirect("customers:complete_profile")

    # --- 4️⃣ Require address info before proceeding ---
    if not service_address or not billing_address_str:
        messages.info(
            request, "Please complete your address details before checkout."
        )
        request.session["next_after_profile"] = "billing:checkout"
        request.session["checkout_pending"] = True
        request.session.modified = True
        return redirect("customers:complete_profile")

    # --- 5️⃣ Handle POST submission ---
    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            billing_data = form.cleaned_data

            # ✅ Update RegisteredCustomer with submitted billing info
            if rc:
                rc.billing_street_address = billing_data.get(
                    "billing_street_address", rc.billing_street_address)
                rc.billing_city = billing_data.get(
                    "billing_city", rc.billing_city)
                rc.billing_state = billing_data.get(
                    "billing_state", rc.billing_state)
                rc.billing_zipcode = billing_data.get(
                    "billing_zipcode", rc.billing_zipcode)
                rc.region = billing_data.get("billing_country", rc.region)
                rc.save(update_fields=[
                    "billing_street_address",
                    "billing_city",
                    "billing_state",
                    "billing_zipcode",
                    "region",
                ])

            # ✅ Store billing data for Stripe session
            request.session["billing_data"] = billing_data
            request.session.modified = True
            return redirect("billing:create_checkout_session")
        else:
            messages.error(
                request, "Please correct the billing form errors below.")
    else:
        form = CheckoutForm(user=request.user)

    # --- 6️⃣ Render checkout summary page ---
    context = {
        "cart": cart,
        "form": form,
        "subtotal": cart.subtotal,
        "tax": cart.tax,
        "total": cart.total,
        "service_address": service_address,
        "billing_address": billing_address_str,
    }
    return render(request, "billing/checkout.html", context)


# ----------------------------------------------------------------------
# 💳 Stripe Checkout Session
# ----------------------------------------------------------------------


@login_required
def create_checkout_session(request):
    """
    Creates a Stripe Checkout Session from the current user's cart.
    """
    from billing.models import Cart

    cart = Cart.objects.filter(
        user=request.user).order_by("-updated_at").first()
    if not cart or not cart.items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("scheduling:search_by_date")

    subtotal = cart.subtotal
    tax = (subtotal * Decimal(str(SALES_TAX_RATE))).quantize(Decimal("0.01"))
    total = (subtotal + tax).quantize(Decimal("0.01"))

    try:
        line_items = [
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Selected Services"},
                    "unit_amount": int(subtotal * 100),
                },
                "quantity": 1,
            }
        ]
        if tax > 0:
            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Sales Tax"},
                        "unit_amount": int(tax * 100),
                    },
                    "quantity": 1,
                }
            )

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=request.build_absolute_uri("/billing/success/"),
            cancel_url=request.build_absolute_uri("/billing/cancel/"),
            customer_email=request.user.email,
            metadata={
                "user_id": request.user.id,
                "subtotal": str(subtotal),
                "tax": str(tax),
                "total": str(total),
            },
        )

        Payment.objects.create(
            user=request.user,
            amount=int(total * 100),  # cents
            currency="usd",
            status=Payment.Status.PROCESSING,
            stripe_checkout_session_id=checkout_session.id,
            description="Cart checkout",
        )

        return redirect(checkout_session.url, code=303)

    except Exception as e:
        messages.error(request, f"Stripe error: {e}")
        return redirect("billing:checkout")


# ----------------------------------------------------------------------
# ✅ Payment Success / Cancel
# ----------------------------------------------------------------------
@login_required
def payment_success(request):
    """
    Stripe payment success handler.
    - Clears and deletes the completed cart.
    - Resets address + session for a new booking.
    - Creates a brand new empty cart while preserving login.
    """
    cleared_count = 0
    old_cart_id = request.session.get("cart_id")

    try:
        # Locate the user's most recent cart
        cart = (
            Cart.objects.filter(user=request.user)
            .order_by("-updated_at")
            .first()
        )

        if cart:
            cleared_count = cart.items.count()
            cart.items.all().delete()
            print(
                f"🧹 Cleared {cleared_count} items from cart {cart.id} for {request.user.username}")
            # Delete the old cart object entirely
            cart.delete()
            print(f"🗑️ Deleted old cart ID {old_cart_id}")

    except Exception as e:
        print(f"⚠️ Error while clearing cart after payment: {e}")

    # --- Reset session state for new booking ---
    for key in ("cart_id", "service_address", "address_locked"):
        request.session.pop(key, None)
    request.session.modified = True

    # --- Create a brand new empty cart for next booking ---
    try:
        from billing.utils import _get_or_create_cart
        new_cart = _get_or_create_cart(request)
        print(
            f"🛒 Created fresh cart ID {new_cart.id} after payment for user {request.user.username}")
    except Exception as e:
        print(f"⚠️ Could not create new cart after payment: {e}")

    messages.success(
        request,
        f"✅ Payment successful! {cleared_count} item(s) booked. "
        "Your cart has been reset for your next booking session.",
    )

    return render(
        request,
        "billing/success.html",
        {"cleared_count": cleared_count,
            "new_cart_id": request.session.get("cart_id")},
    )


def payment_cancel(request):
    """Renders Stripe payment cancellation page."""
    return render(request, "billing/cancel.html")
# ----------------------------------------------------------------------
# 🧾 Payment History (user)
# ----------------------------------------------------------------------


@login_required
def payment_history(request):
    payments = Payment.objects.filter(
        user=request.user).order_by("-created_at")
    total_spent = payments.aggregate(Sum("amount"))["amount__sum"] or 0

    return render(request, "billing/payment_history.html", {
        "payments": payments,
        "total_spent": total_spent / 100,
    })


# ----------------------------------------------------------------------
# 🧾 All Payments (admin)
# ----------------------------------------------------------------------
@user_passes_test(lambda u: u.is_superuser)
def all_payments_admin(request):
    payments = Payment.objects.select_related("user").order_by("-created_at")
    total_volume = payments.aggregate(Sum("amount"))["amount__sum"] or 0

    return render(request, "billing/all_payments_admin.html", {
        "payments": payments,
        "total_volume": total_volume / 100,
    })


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def refund_payment(request, pk):
    """Allows admin to issue Stripe refunds."""
    payment = get_object_or_404(Payment, pk=pk)
    try:
        payment.refund()
        messages.success(
            request, f"Refund issued for {payment.user.username}.")
    except Exception as e:
        messages.error(request, f"Refund failed: {e}")
    return redirect("billing:all_payments_admin")


# ----------------------------------------------------------------------
# 🌐 Stripe Webhook Listener
# ----------------------------------------------------------------------
@csrf_exempt
def stripe_webhook(request):
    """
    Receives events from Stripe (payment succeeded, refund, failure, etc.)
    """
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    try:
        if endpoint_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret)
        else:
            event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key)
    except Exception:
        return HttpResponse(status=400)

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "payment_intent.succeeded":
        Payment.objects.filter(
            stripe_payment_intent_id=data["id"]).update(status="succeeded")

    elif event_type == "charge.refunded":
        Payment.objects.filter(
            stripe_payment_intent_id=data.get("payment_intent")
        ).update(status="refunded")

    elif event_type == "payment_intent.payment_failed":
        Payment.objects.filter(
            stripe_payment_intent_id=data["id"]).update(status="canceled")

    return HttpResponse(status=200)

# =========================================================
# 🛒 CART UTILITIES
# =========================================================


# =========================================================
#  CART VIEWS
# =========================================================
@require_POST
def cart_add(request):
    """
    Adds a booking item to the cart.
    Clears cart if address in session differs from existing cart.
    """
    from billing.constants import SERVICE_PRICES

    cart = _get_or_create_cart(request)

    # 🔒 Ensure the session's address is locked to this cart
    service_address = request.session.get("service_address")
    cart_address = cart.address_key or ""

    if normalize_address(service_address) != normalize_address(cart_address):
        cart.clear()
        cart.address_key = service_address.strip() or None
        cart.save(update_fields=["address_key", "updated_at"])
        messages.warning(
            request,
            "Your previous cart was cleared because you selected a different service address. "
            "Each session is tied to one address only."
        )

    employee_id = request.POST.get("employee_id")
    service_id = request.POST.get("service_category_id")
    slot_id = request.POST.get("time_slot_id")
    date_str = request.POST.get("date")

    if not all([employee_id, service_id, slot_id, date_str]):
        return JsonResponse({"ok": False, "error": "Missing parameters."}, status=400)

    # ⏰ Parse date
    from datetime import datetime as dt
    try:
        date_obj = dt.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"ok": False, "error": "Bad date format."}, status=400)

    # 🔍 Lookup related models
    from scheduling.models import Employee, ServiceCategory, TimeSlot
    try:
        employee = Employee.objects.get(pk=employee_id)
        service = ServiceCategory.objects.get(pk=service_id)
        slot = TimeSlot.objects.get(pk=slot_id)
    except (Employee.DoesNotExist, ServiceCategory.DoesNotExist, TimeSlot.DoesNotExist):
        return JsonResponse({"ok": False, "error": "Invalid reference."}, status=404)

    # 💲 Compute pre-tax price (2h per slot)
    from decimal import Decimal
    base_rate = Decimal(str(SERVICE_PRICES.get(service.name, 25.00)))
    hours = Decimal("2")
    unit_price_pre_tax = (base_rate * hours).quantize(Decimal("0.01"))

    # --- Prevent mixing addresses within one session ---
    current_service_addr = request.session.get("service_address", "")
    if cart.address_key and normalize_address(cart.address_key) != normalize_address(current_service_addr):
        cart.items.all().delete()
        cart.address_key = current_service_addr
        cart.save(update_fields=["address_key"])
        print(
            f"⚠️ Cart cleared due to new service address: {current_service_addr}")

    # 🧾 Add or update the cart item
    from billing.models import CartItem
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        employee=employee,
        service_category=service,
        time_slot=slot,
        date=date_obj,
        defaults={"unit_price": unit_price_pre_tax, "quantity": 1},
    )
    if not created:
        item.unit_price = unit_price_pre_tax
        item.save(update_fields=["unit_price"])

    # 🔄 Render updated cart partial
    from django.template.loader import render_to_string
    html = render_to_string("scheduling/_cart.html",
                            {"cart": cart}, request=request)
    summary_text = f"({cart.items.count()}) – (${cart.total:.2f})"

    return JsonResponse({
        "ok": True,
        "html": html,
        "count": cart.items.count(),
        "subtotal": f"{cart.subtotal:.2f}",
        "total": f"{cart.total:.2f}",
        "summary_text": summary_text,
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
    return JsonResponse({"ok": True,
                         "html": render_to_string("scheduling/_cart.html", {"cart": cart}, request=request),
                         "total": str(cart.total),
                         "summary_text": f"({cart.items.count()}) – (${cart.total:.2f})"})


@require_POST
def cart_clear(request):
    cart = _get_or_create_cart(request)
    cart.items.all().delete()
    html = render_to_string("scheduling/_cart.html",
                            {"cart": cart}, request=request)
    return JsonResponse({"ok": True,
                         "html": render_to_string("scheduling/_cart.html", {"cart": cart}, request=request),
                         "count": 0,
                         "total": "0.00",
                         "summary_text": f"({cart.items.count()}) – (${cart.total:.2f})"
                         })


def cart_detail(request):
    """Optional full-page cart view (non-AJAX)."""
    cart = _get_or_create_cart(request)
    get_token(request)  # ensure CSRF cookie
    return render(request, "scheduling/cart_detail.html", {"cart": cart})
