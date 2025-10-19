"""
billing/views.py
Handles checkout, Stripe integration, payment tracking, and admin management.
"""

import json
import stripe
from decimal import Decimal
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
    Displays a summary of selected services before Stripe payment.
    """
    selected_services = []
    hours = 0
    subtotal = Decimal("0.00")
    tax = Decimal("0.00")
    total = Decimal("0.00")

    if request.method == "POST":
        selected_services = request.POST.getlist("services[]")
        hours = int(request.POST.get("hours", 2))  # default 2 hours

        subtotal = sum(
            Decimal(SERVICE_PRICES[s]) * hours for s in selected_services)
        tax = (subtotal * Decimal(SALES_TAX_RATE)).quantize(Decimal("0.01"))
        total = (subtotal + tax).quantize(Decimal("0.01"))

        context = {
            "selected_services": selected_services,
            "hours": hours,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
        }
        return render(request, "billing/checkout.html", context)

    return render(request, "billing/checkout.html", {
        "selected_services": selected_services,
        "hours": hours,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
    })


# ----------------------------------------------------------------------
# 💳 Stripe Checkout Session
# ----------------------------------------------------------------------
@login_required
def create_checkout_session(request):
    """
    Creates a Stripe Checkout Session and redirects to Stripe's hosted page.
    """
    if not hasattr(request.user, "registeredcustomer"):
        return redirect("customers:register")

    if request.method == "POST":
        selected_services = request.POST.getlist("services[]")
        hours = int(request.POST.get("hours", 2))

        subtotal = sum(SERVICE_PRICES[s] * hours for s in selected_services)
        tax = round(subtotal * SALES_TAX_RATE, 2)
        total = round(subtotal + tax, 2)

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {"name": "Selected Services"},
                            "unit_amount": int(subtotal * 100),
                        },
                        "quantity": 1,
                    },
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {"name": f"Sales Tax ({SALES_TAX_RATE*100:.2f}%)"},
                            "unit_amount": int(tax * 100),
                        },
                        "quantity": 1,
                    },
                ],
                mode="payment",
                success_url=request.build_absolute_uri("/billing/success/"),
                cancel_url=request.build_absolute_uri("/billing/cancel/"),
                customer_email=request.user.email,
                metadata={
                    "user_id": request.user.id,
                    "services": ",".join(selected_services),
                    "subtotal": str(subtotal),
                    "tax": str(tax),
                    "total": str(total),
                },
            )

            Payment.objects.create(
                user=request.user,
                amount=int(total * 100),
                currency="usd",
                status=Payment.Status.PROCESSING,
                stripe_checkout_session_id=checkout_session.id,
                description=f"Services: {', '.join(selected_services)}",
            )

            return redirect(checkout_session.url, code=303)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return redirect("billing:checkout")


# ----------------------------------------------------------------------
# ✅ Payment Success / Cancel
# ----------------------------------------------------------------------
def payment_success(request):
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
