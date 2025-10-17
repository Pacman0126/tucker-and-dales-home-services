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
from .models import Payment
from core.constants import SERVICE_PRICES, TAX_RATE


# Create your views here.
# configure stripe keys
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def checkout(request):
    # Require profile completion first
    if not hasattr(request.user, "customer_profile"):
        return redirect("customers:complete_profile")


@login_required
def create_checkout_session(request):
    """Create a Stripe Checkout Session and return its URL."""

    try:
        # example: total from cart (replace with your basket total)
        total_cents = 2500  # $25.00

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,
                    "product_data": {"name": "Tucker & Dale’s Home Service"},
                    "unit_amount": total_cents,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=request.build_absolute_uri("/billing/success/"),
            cancel_url=request.build_absolute_uri("/billing/cancel/"),
            customer_email=request.user.email,
        )

        # store in DB
        Payment.objects.create(
            user=request.user,
            amount=total_cents,
            status=Payment.Status.PROCESSING,
            stripe_checkout_session_id=checkout_session.id,
            description="Service Booking",
        )

        return JsonResponse({"sessionUrl": checkout_session.url})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def payment_success(request):
    return render(request, "billing/success.html")


def payment_cancel(request):
    return render(request, "billing/cancel.html")


@login_required
def payment_history(request):
    """
    Display the logged-in user's payment records.
    """
    payments = Payment.objects.filter(
        user=request.user).order_by("-created_at")
    total_spent = payments.aggregate(Sum("amount"))["amount__sum"] or 0

    context = {
        "payments": payments,
        "total_spent": total_spent / 100,  # convert cents → dollars
    }
    return render(request, "billing/payment_history.html", context)


@user_passes_test(lambda u: u.is_superuser)
def all_payments_admin(request):
    """
    Superuser-only dashboard for all payments.
    """
    payments = Payment.objects.select_related("user").order_by("-created_at")
    total_volume = payments.aggregate(Sum("amount"))["amount__sum"] or 0

    context = {
        "payments": payments,
        "total_volume": total_volume / 100,
    }
    return render(request, "billing/all_payments_admin.html", context)


@user_passes_test(lambda u: u.is_superuser)
@require_POST
def refund_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    try:
        payment.refund()
        messages.success(
            request, f"Refund issued for {payment.user.username}.")
    except Exception as e:
        messages.error(request, f"Refund failed: {e}")
    return redirect("billing:all_payments_admin")


@csrf_exempt
def stripe_webhook(request):
    """
    Receives and handles Stripe webhook events (payment + refund updates).
    """
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature", None)
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    try:
        if endpoint_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        else:
            event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key
            )
    except Exception as e:
        return HttpResponse(status=400)

    event_type = event["type"]
    data = event["data"]["object"]

    # --- Handle events ---
    if event_type == "payment_intent.succeeded":
        Payment.objects.filter(
            stripe_payment_intent_id=data["id"]
        ).update(status="succeeded")

    elif event_type == "charge.refunded":
        intent_id = data.get("payment_intent")
        Payment.objects.filter(
            stripe_payment_intent_id=intent_id
        ).update(status="refunded")

    elif event_type == "payment_intent.payment_failed":
        Payment.objects.filter(
            stripe_payment_intent_id=data["id"]
        ).update(status="canceled")

    return HttpResponse(status=200)


@login_required
def create_checkout_session(request):
    if request.method == "POST":
        selected_services = request.POST.getlist(
            "services[]")  # e.g. ["house_cleaning", "lawncare"]
        hours = int(request.POST.get("hours", 2))  # default 2 hours per block

        subtotal = sum(SERVICE_PRICES[s] * hours for s in selected_services)
        tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax, 2)

        stripe.api_key = settings.STRIPE_SECRET_KEY

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": ", ".join(selected_services)},
                        "unit_amount": int(total * 100),  # in cents
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=request.build_absolute_uri("/billing/success/"),
            cancel_url=request.build_absolute_uri("/billing/cancel/"),
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
            description=f"Services: {', '.join(selected_services)}"
        )

        return redirect(checkout_session.url, code=303)

    return render(request, "billing/checkout.html")
