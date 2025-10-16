import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from .models import Payment

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


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks (e.g., payment succeeded)."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        Payment.objects.filter(
            stripe_checkout_session_id=session["id"]
        ).update(status=Payment.Status.SUCCEEDED)

    return HttpResponse(status=200)


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
