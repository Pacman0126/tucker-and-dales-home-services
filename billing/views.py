"""
billing/views.py
Handles checkout, Stripe integration, payment tracking, and admin management.
"""

import json
from decimal import Decimal
import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum

from core.constants import SERVICE_PRICES, SALES_TAX_RATE
from .models import Payment
from scheduling.models import Cart

# ----------------------------------------------------------------------
# ⚙️ Stripe Setup
# ----------------------------------------------------------------------
stripe.api_key = settings.STRIPE_SECRET_KEY


# ----------------------------------------------------------------------
# 🏁 Simple Checkout Page (called by navbar burger)
# ----------------------------------------------------------------------
def _get_or_create_cart(request):
    """
    Shared helper for retrieving the active cart.
    Works for both logged-in users and anonymous sessions.
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(
            session_key=request.session.session_key)
    return cart


@login_required
def checkout(request):
    """
    Renders the primary checkout page where the user confirms and pays.
    This is the entry point triggered by the navbar burger icon.
    """
    context = {
        "selected_services": [],
        "hours": 0,
        "subtotal": Decimal("0.00"),
        "tax": Decimal("0.00"),
        "total": Decimal("0.00"),
    }
    return render(request, "billing/checkout.html", context)


# ----------------------------------------------------------------------
# 🧾 Checkout Summary (pre-Stripe)
# ----------------------------------------------------------------------
@login_required
def checkout_summary(request):
    """
    Shows the cart summary before payment.
    Auto-fills service/billing addresses from session or RegisteredCustomer.
    """
    cart = _get_or_create_cart(request)
    if not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("scheduling:search_by_date")

    from .forms import CheckoutForm
    from customers.models import RegisteredCustomer

    # --- Load address defaults ---
    service_address = request.session.get("service_address")
    billing_address = request.session.get("billing_address")

    if not service_address or not billing_address:
        try:
            rc = RegisteredCustomer.objects.get(user=request.user)
            if all([rc.street_address, rc.city, rc.state, rc.zipcode]):
                full_addr = f"{rc.street_address}, {rc.city}, {rc.state} {rc.zipcode}"
                service_address = service_address or full_addr
                billing_address = billing_address or full_addr
                request.session["service_address"] = service_address
                request.session["billing_address"] = billing_address
                request.session.modified = True
            else:
                messages.info(
                    request, "Please complete your address details before checkout.")
                return redirect("customers:complete_profile")
        except RegisteredCustomer.DoesNotExist:
            messages.info(
                request, "Please complete your profile before checkout.")
            return redirect("customers:complete_profile")

    # --- Standard checkout form flow ---
    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            request.session["billing_data"] = form.cleaned_data
            return redirect("billing:create_checkout_session")
    else:
        form = CheckoutForm(user=request.user)

    context = {
        "cart": cart,
        "form": form,
        "subtotal": cart.subtotal,
        "tax": cart.tax,
        "total": cart.total,
        "service_address": service_address,
        "billing_address": billing_address,
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
    from scheduling.models import Cart

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
    Renders success confirmation after Stripe payment
    and clears the user's active cart.
    """
    from scheduling.models import Cart

    # Clear cart items for this user
    cart = Cart.objects.filter(
        user=request.user).order_by("-updated_at").first()
    if cart:
        cart.items.all().delete()

    messages.success(
        request, "✅ Payment successful! Your cart has been cleared.")
    return render(request, "billing/success.html")


def payment_cancel(request):
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
