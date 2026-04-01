"""
billing/views.py
Handles checkout, Stripe integration, payment tracking, and admin management.
"""

from io import BytesIO
from datetime import datetime as dt
from decimal import Decimal

import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models, transaction
from django.db.models import Sum
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import localdate, now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from billing.constants import SALES_TAX_RATE, SERVICE_PRICES
from billing.models import Cart, CartItem, Payment, PaymentHistory
from billing.utils import send_payment_receipt_email

from core.decorators import verified_email_required, login_required_json
from scheduling.models import Booking
from .utils import _get_or_create_cart, normalize_address, get_refund_policy

stripe.api_key = settings.STRIPE_SECRET_KEY

PENALTY_WINDOW_HOURS = 72


def _penalty_applies(booking: Booking) -> bool:
    """True if within 72h window from now."""
    start_dt = getattr(booking, "datetime_start", None)
    if start_dt:
        hours = (start_dt - now()).total_seconds() / 3600.0
    else:
        hours = (booking.date - localdate()).days * 24.0
    return hours < PENALTY_WINDOW_HOURS


def _cart_has_past_dates(cart) -> bool:
    """
    Return True if any cart item is dated before today.
    """
    if not cart:
        return False
    today = timezone.localdate()
    return cart.items.filter(date__lt=today).exists()

# ----------------------------------------------------------------------
# 🏁 Simple Checkout Page
# ----------------------------------------------------------------------
# @login_required
# @verified_email_required
# @require_POST
# def create_checkout_session(request):
#     """
#     Initiates a Stripe Checkout session for the active cart.
#     Saves all totals and cart metadata for Stripe webhooks.

#     Defensive validation:
#     - blocks checkout if any cart item is in the past
#     """
#     from billing.utils import get_active_cart_for_request

#     stripe.api_key = settings.STRIPE_SECRET_KEY

#     cart = get_active_cart_for_request(request, create_if_missing=False)
#     if not cart or not cart.items.exists():
#         messages.warning(request, "Your cart is empty.")
#         return redirect("billing:checkout")

#     if _cart_has_past_dates(cart):
#         messages.error(
#             request,
#             "Past dates cannot be booked. Please remove past-dated services from your cart.",
#         )
#         return redirect("billing:checkout")

#     subtotal = cart.subtotal
#     tax = cart.tax
#     total = cart.total
#     service_address = request.session.get(
#         "service_address", "") or cart.address_key or ""

#     request.session["cart_id"] = cart.pk
#     request.session.modified = True

#     success_url = (
#         request.build_absolute_uri(reverse("billing:payment_success"))
#         + "?session_id={CHECKOUT_SESSION_ID}"
#     )
#     cancel_url = request.build_absolute_uri(reverse("billing:checkout"))

#     metadata = {
#         "subtotal": f"{subtotal:.2f}",
#         "tax": f"{tax:.2f}",
#         "total": f"{total:.2f}",
#         "service_address": service_address,
#         "cart_id": str(cart.pk),
#         "user_id": str(request.user.id),
#         "username": request.user.username,
#     }

#     try:
#         checkout_session = stripe.checkout.Session.create(
#             mode="payment",
#             payment_method_types=["card"],
#             line_items=[
#                 {
#                     "price_data": {
#                         "currency": "usd",
#                         "product_data": {"name": "Home Services Booking"},
#                         "unit_amount": int(total * Decimal("100")),
#                     },
#                     "quantity": 1,
#                 }
#             ],
#             success_url=success_url,
#             cancel_url=cancel_url,
#             metadata=metadata,
#             payment_intent_data={
#                 "metadata": metadata,
#             },
#         )

#         request.session["last_checkout_session_id"] = checkout_session.id
#         request.session.modified = True
#         return redirect(checkout_session.url, code=303)

#     except Exception as e:
#         print("Stripe create session error:", e)
#         messages.error(request, f"Could not start checkout: {e}")
#         return redirect("billing:checkout")


@login_required
@verified_email_required
def checkout(request):
    """
    Displays the user's active cart summary and recalculates totals before
    Stripe checkout. Uses the same active cart resolution as the rest of the
    booking flow so navbar, cart, checkout, and payment success stay in sync.
    """
    from billing.utils import get_active_cart_for_request

    cart = get_active_cart_for_request(request, create_if_missing=False)

    if not cart or not cart.items.exists():
        messages.info(
            request,
            "Your cart is empty — please add services before checkout.",
        )
        return redirect("scheduling:search_by_time_slot")

    if request.method == "POST" and "selected_items" in request.POST:
        ids_to_remove = request.POST.getlist("selected_items")
        if ids_to_remove:
            CartItem.objects.filter(cart=cart, id__in=ids_to_remove).delete()
            cart.refresh_from_db()
            messages.success(
                request,
                f"Removed {len(ids_to_remove)} item(s) from your cart.",
            )
            return redirect("billing:checkout")

    subtotal = sum(
        (item.unit_price or Decimal("0.00"))
        for item in cart.items.all()
    )
    tax_rate = Decimal(getattr(settings, "SALES_TAX_RATE", 0.0825))
    tax = (subtotal * tax_rate).quantize(Decimal("0.01"))
    total = (subtotal + tax).quantize(Decimal("0.01"))

    context = {
        "cart": cart,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "SALES_TAX_RATE": tax_rate,
    }
    return render(request, "billing/checkout.html", context)


# ----------------------------------------------------------------------
# 🧾 Checkout Summary (pre-Stripe)
# ----------------------------------------------------------------------
@login_required
@verified_email_required
def checkout_summary(request):
    """
    Displays the cart summary before payment.
    Uses the active cart pinned in the session (cart_id),
    ensuring address and billing details are consistent.
    """
    from billing.utils import get_active_cart_for_request, get_service_address
    from customers.models import CustomerProfile
    from .forms import CheckoutForm

    cart = get_active_cart_for_request(request, create_if_missing=False)
    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("scheduling:search_by_date")

    service_address = get_service_address(request)

    billing_address_str = request.session.get("billing_address", "")
    rc = None
    try:
        rc = CustomerProfile.objects.get(user=request.user)
        if not billing_address_str and rc.has_valid_billing_address():
            billing_address_str = rc.full_billing_address
            request.session["billing_address"] = billing_address_str
            request.session.modified = True
    except CustomerProfile.DoesNotExist:
        messages.info(request, "Please complete your profile before checkout.")
        request.session["next_after_profile"] = "billing:checkout"
        request.session["checkout_pending"] = True
        request.session.modified = True
        return redirect("customers:complete_profile")

    if not service_address or not billing_address_str:
        messages.info(
            request, "Please complete your address details before checkout.")
        request.session["next_after_profile"] = "billing:checkout"
        request.session["checkout_pending"] = True
        request.session.modified = True
        return redirect("customers:complete_profile")

    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            billing_data = form.cleaned_data

            if rc:
                rc.billing_street_address = billing_data.get(
                    "billing_street_address", rc.billing_street_address
                )
                rc.billing_city = billing_data.get(
                    "billing_city", rc.billing_city)
                rc.billing_state = billing_data.get(
                    "billing_state", rc.billing_state)
                rc.billing_zipcode = billing_data.get(
                    "billing_zipcode", rc.billing_zipcode)
                rc.region = billing_data.get("billing_country", rc.region)
                rc.save(
                    update_fields=[
                        "billing_street_address",
                        "billing_city",
                        "billing_state",
                        "billing_zipcode",
                        "region",
                    ]
                )

            request.session["billing_data"] = billing_data
            request.session.modified = True
            return redirect("billing:create_checkout_session")

        messages.error(
            request, "Please correct the billing form errors below.")
    else:
        form = CheckoutForm(user=request.user)

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
@verified_email_required
@require_POST
def create_checkout_session(request):
    """
    Initiates a Stripe Checkout session for the active cart.
    Saves totals and cart metadata for Stripe webhooks.

    Defensive validation:
    - blocks checkout if cart is empty
    - blocks checkout if any cart item is in the past

    Address design:
    - service_address stays tied to the booked jobsite
    - billing address remains separate and may differ
    - Stripe Checkout email is prefilled from the authenticated user
    """
    from billing.utils import get_active_cart_for_request

    stripe.api_key = settings.STRIPE_SECRET_KEY

    cart = get_active_cart_for_request(request, create_if_missing=False)
    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("billing:checkout")

    if _cart_has_past_dates(cart):
        messages.error(
            request,
            "Past dates cannot be booked. Please remove past-dated services from your cart.",
        )
        return redirect("billing:checkout")

    subtotal = cart.subtotal
    tax = cart.tax
    total = cart.total

    # Service/jobsite address used for booking fulfillment and payment linkage
    service_address = (
        request.session.get("service_address", "") or cart.address_key or ""
    ).strip()

    # Billing address remains conceptually separate from service address.
    # Keep it in metadata only as optional context; do not use it to replace
    # the service address used for booking/payment history grouping.
    billing_address = (
        request.session.get("billing_address", "") or ""
    ).strip()

    request.session["cart_id"] = cart.pk
    request.session.modified = True

    success_url = (
        request.build_absolute_uri(reverse("billing:payment_success"))
        + "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = request.build_absolute_uri(reverse("billing:checkout"))

    metadata = {
        "subtotal": f"{subtotal:.2f}",
        "tax": f"{tax:.2f}",
        "total": f"{total:.2f}",
        "service_address": service_address,
        "billing_address": billing_address,
        "cart_id": str(cart.pk),
        "user_id": str(request.user.id),
        "username": request.user.username,
    }

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            customer_email=(request.user.email or None),
            billing_address_collection="required",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Home Services Booking"},
                        "unit_amount": int(total * Decimal("100")),
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            payment_intent_data={
                "metadata": metadata,
            },
        )

        request.session["last_checkout_session_id"] = checkout_session.id
        request.session.modified = True
        return redirect(checkout_session.url, code=303)

    except Exception as e:
        print("Stripe create session error:", e)
        messages.error(request, f"Could not start checkout: {e}")
        return redirect("billing:checkout")


# ----------------------------------------------------------------------
# ✅ Payment Success / Cancel
# ----------------------------------------------------------------------
@login_required
@verified_email_required
def payment_cancel(request):
    """Handles user cancellation from Stripe checkout."""
    messages.info(
        request, "Your payment was cancelled — no charges were made.")
    return redirect("billing:checkout")


# ----------------------------------------------------------------------
# 🧾 Payment History helpers
# ----------------------------------------------------------------------
def _refresh_booking_statuses_for_user(user):
    """Auto-refresh status for user's bookings (Completed / Active)."""
    today = now().date()
    bookings = Booking.objects.filter(user=user)
    for booking in bookings:
        if booking.date < today and booking.status != "Completed":
            booking.status = "Completed"
            booking.save(update_fields=["status"])
        elif booking.date >= today and booking.status == "Completed":
            booking.status = "Booked"
            booking.save(update_fields=["status"])


# ----------------------------------------------------------------------
# 🧾 Download receipt PDF
# ----------------------------------------------------------------------
@login_required
@verified_email_required
def download_receipt_pdf(request, pk):
    """Generate a detailed PDF receipt with grouped adjustments."""
    root = get_object_or_404(
        PaymentHistory, id=pk, user=request.user, parent__isnull=True
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph("<b>Tucker & Dale’s Home Services</b>", styles["Title"])
    )
    elements.append(
        Paragraph(
            f"Receipt generated: {now().strftime('%Y-%m-%d %H:%M')}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.25 * inch))

    elements.append(
        Paragraph(
            f"<b>Service Address:</b> {root.service_address}",
            styles["Normal"],
        )
    )
    elements.append(
        Paragraph(
            f"<b>Transaction ID:</b> {root.stripe_payment_id or 'N/A'}",
            styles["Normal"],
        )
    )
    elements.append(
        Paragraph(f"<b>Status:</b> {root.status}", styles["Normal"])
    )
    elements.append(Spacer(1, 0.25 * inch))

    def make_table(title, rows, color):
        elements.append(Paragraph(f"<b>{title}</b>", styles["Heading4"]))
        data = [["Date", "Description", "Amount (USD)"]] + rows
        table = Table(data, colWidths=[1.5 * inch, 3.5 * inch, 1.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 0.15 * inch))

    make_table(
        "Original Services",
        [[
            root.created_at.strftime("%Y-%m-%d"),
            root.notes or "Initial Booking Payment",
            f"${root.amount:.2f}",
        ]],
        colors.green,
    )

    cancelled = PaymentHistory.objects.filter(
        parent=root,
        amount__lt=0,
    ).order_by("created_at")

    if cancelled.exists():
        rows = [
            [
                adj.created_at.strftime("%Y-%m-%d"),
                adj.notes or "Cancelled Service",
                f"-${abs(adj.amount):.2f}",
            ]
            for adj in cancelled
        ]
        make_table("Cancelled / Refunded Services", rows, colors.red)

    added = PaymentHistory.objects.filter(
        parent=root,
        amount__gt=0,
    ).order_by("created_at")

    if added.exists():
        rows = [
            [
                adj.created_at.strftime("%Y-%m-%d"),
                adj.notes or "Added Service",
                f"${adj.amount:.2f}",
            ]
            for adj in added
        ]
        make_table("Added Services / Adjustments", rows, colors.blue)

    original_total, add_total, cancel_total, net_total = root.compute_sections()

    summary_rows = [
        ["Original Total", f"${original_total:.2f}"],
        ["Added Services", f"${add_total:.2f}"],
        ["Cancelled / Refunded", f"-${abs(cancel_total):.2f}"],
        ["Net Total", f"${net_total:.2f}"],
    ]
    summary_table = Table(summary_rows, colWidths=[4.5 * inch, 2.0 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("<b>Summary</b>", styles["Heading4"]))
    elements.append(summary_table)

    doc.build(elements)
    buffer.seek(0)

    filename = f"receipt_{root.id}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
@verified_email_required
def download_yearly_summary_pdf(request):
    """
    Generate a combined summary PDF of all PaymentHistory chains
    for this user, grouped by service_address.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph("<b>Tucker & Dale’s Home Services</b>", styles["Title"]))
    elements.append(
        Paragraph(f"Annual Summary for {request.user.username}", styles["Normal"]))
    elements.append(
        Paragraph(
            f"Generated: {now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"])
    )
    elements.append(Spacer(1, 0.3 * inch))

    roots = (
        PaymentHistory.objects.filter(user=request.user, parent__isnull=True)
        .select_related("user")
        .order_by("service_address", "-created_at")
    )

    grouped = {}
    for root in roots:
        grouped.setdefault(root.service_address, []).append(root)

    grand_total = Decimal("0.00")

    for address, chains in grouped.items():
        elements.append(Paragraph(f"<b>🏠 {address}</b>", styles["Heading2"]))
        elements.append(Spacer(1, 0.1 * inch))

        property_total = Decimal("0.00")

        for root in chains:
            original_total, add_total, cancel_total, net_total = root.compute_sections()
            property_total += net_total

            data = [
                ["Date", "Original", "Added", "Refunded", "Adjusted Total"],
                [
                    root.created_at.strftime("%Y-%m-%d"),
                    f"${original_total:.2f}",
                    f"+${add_total:.2f}" if add_total > 0 else "$0.00",
                    f"-${abs(cancel_total):.2f}" if cancel_total else "$0.00",
                    f"${net_total:.2f}",
                ],
            ]
            table = Table(
                data,
                colWidths=[1.3 * inch, 1.3 * inch,
                           1.3 * inch, 1.3 * inch, 1.3 * inch],
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ]
                )
            )
            elements.append(table)
            elements.append(Spacer(1, 0.1 * inch))

        elements.append(
            Paragraph(
                f"<b>Total for {address}:</b> ${property_total:.2f}", styles["Normal"])
        )
        elements.append(Spacer(1, 0.3 * inch))
        grand_total += property_total

    elements.append(Spacer(1, 0.5 * inch))
    elements.append(
        Paragraph("<b>Grand Total Across All Properties</b>", styles["Heading3"]))
    elements.append(Paragraph(f"<b>${grand_total:.2f}</b>", styles["Title"]))
    elements.append(Spacer(1, 0.3 * inch))

    doc.build(elements)
    buffer.seek(0)

    filename = f"Yearly_Summary_{request.user.username}_{now().year}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


# ----------------------------------------------------------------------
# 🧾 All Payments (admin)
# ----------------------------------------------------------------------
@user_passes_test(lambda u: u.is_superuser)
def all_payments_admin(request):
    payments = Payment.objects.select_related("user").order_by("-created_at")
    total_volume = payments.aggregate(Sum("amount"))["amount__sum"] or 0

    return render(
        request,
        "billing/all_payments_admin.html",
        {
            "payments": payments,
            "total_volume": total_volume / 100,
        },
    )


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
@require_POST
def stripe_webhook(request):
    """
    Handles Stripe webhook events safely and idempotently.

    Important design rule:
    - Webhook records the root PaymentHistory only.
    - Webhook does NOT guess or relink Bookings by address.
    - Booking creation/linking is finalized by payment_success(), which has
      the validated checkout session + cart context.

    Why:
    - Prevents a cancelled booking from being reused and attached to a new
      payment simply because it shares the same service address.
    """
    from django.contrib.auth import get_user_model

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            endpoint_secret,
        )
    except ValueError as e:
        print(f"❌ Webhook payload error: {e}")
        return HttpResponseBadRequest("Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        print(f"❌ Webhook signature error: {e}")
        return HttpResponseBadRequest("Invalid signature")

    event_type = event.get("type")

    if event_type != "payment_intent.succeeded":
        print(f"ℹ️ Webhook event received: {event_type} (ignored)")
        return HttpResponse(status=200)

    intent = event["data"]["object"]
    stripe_payment_id = intent.get("id")
    amount = Decimal(intent.get("amount_received", 0)) / Decimal("100")
    metadata = intent.get("metadata", {}) or {}

    user_id = metadata.get("user_id")
    service_address = (metadata.get("service_address") or "").strip()
    cart_id = metadata.get("cart_id")

    User = get_user_model()
    user = User.objects.filter(id=user_id).first() if user_id else None

    # Idempotency: Stripe may retry delivery of the same event/payment intent.
    existing_payment = PaymentHistory.objects.filter(
        stripe_payment_id=stripe_payment_id,
        parent__isnull=True,
    ).first()

    if existing_payment:
        print(
            f"ℹ️ Webhook skipped duplicate PaymentHistory for {stripe_payment_id}"
        )
        return HttpResponse(status=200)

    payment = PaymentHistory.objects.create(
        user=user,
        amount=amount,
        adjustments_total_amt=Decimal("0.00"),
        currency="USD",
        status="Paid",
        payment_type="Stripe Webhook Payment",
        stripe_payment_id=stripe_payment_id,
        service_address=service_address or "Unknown",
        raw_data=event,
        notes=(
            "Initial booking payment (via webhook)"
            if not cart_id
            else f"Initial booking payment (via webhook, cart_id={cart_id})"
        ),
    )

    print(
        f"💾 [Webhook] PaymentHistory #{payment.id} recorded for user "
        f"{user.username if user else 'Unknown'} "
        f"(stripe_payment_id={stripe_payment_id}, amount=${amount})"
    )

    # Do NOT attach/reassign bookings here.
    # payment_success() is the only place that should create/link Bookings
    # using the validated checkout session + cart contents.

    return HttpResponse(status=200)


# =========================================================
# CART VIEWS
# =========================================================
@login_required_json
@require_POST
def cart_add(request):
    """
    Adds a booking item to the cart.
    Clears cart if address in session differs from existing cart.

    Defensive validation:
    - blocks adding past-dated services to the cart
    """
    cart = _get_or_create_cart(request)

    service_address = request.session.get("service_address")
    cart_address = cart.address_key or ""

    if normalize_address(service_address) != normalize_address(cart_address):
        cart.clear()
        cart.address_key = service_address.strip() or None
        cart.save(update_fields=["address_key", "updated_at"])
        messages.warning(
            request,
            "Your previous cart was cleared because you selected a different service address. "
            "Each session is tied to one address only.",
        )

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

    today = timezone.localdate()
    if date_obj < today:
        return JsonResponse(
            {"ok": False, "error": "Past dates cannot be booked."},
            status=400,
        )

    from scheduling.models import Employee, ServiceCategory, TimeSlot

    try:
        employee = Employee.objects.get(pk=employee_id)
        service = ServiceCategory.objects.get(pk=service_id)
        slot = TimeSlot.objects.get(pk=slot_id)
    except (Employee.DoesNotExist, ServiceCategory.DoesNotExist, TimeSlot.DoesNotExist):
        return JsonResponse({"ok": False, "error": "Invalid reference."}, status=404)

    base_rate = Decimal(str(SERVICE_PRICES.get(service.name, 25.00)))
    hours = Decimal("2")
    unit_price_pre_tax = (base_rate * hours).quantize(Decimal("0.01"))

    current_service_addr = request.session.get("service_address", "")
    if cart.address_key and normalize_address(cart.address_key) != normalize_address(
        current_service_addr
    ):
        cart.items.all().delete()
        cart.address_key = current_service_addr
        cart.save(update_fields=["address_key"])
        print(
            f"⚠️ Cart cleared due to new service address: {current_service_addr}"
        )

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

    html = render_to_string("billing/_cart.html",
                            {"cart": cart}, request=request)
    summary_text = f"({cart.items.count()}) - (${cart.total:.2f})"

    return JsonResponse(
        {
            "ok": True,
            "html": html,
            "count": cart.items.count(),
            "subtotal": f"{cart.subtotal:.2f}",
            "total": f"{cart.total:.2f}",
            "summary_text": summary_text,
        }
    )


@login_required_json
@require_POST
def cart_remove(request):
    cart = _get_or_create_cart(request)
    item_id = request.POST.get("item_id")
    try:
        item = cart.items.get(pk=item_id)
    except CartItem.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Not found."}, status=404)

    item.delete()
    return JsonResponse(
        {
            "ok": True,
            "html": render_to_string("billing/_cart.html", {"cart": cart}, request=request),
            "total": str(cart.total),
            "summary_text": f"({cart.items.count()}) – (${cart.total:.2f})",
        }
    )


@login_required_json
@require_POST
def remove_selected_from_cart(request):
    """
    Removes selected cart items from the user's active cart.
    Uses the same active cart resolution as checkout/navbar/cart flows.
    """
    from billing.utils import get_active_cart_for_request

    selected_ids = request.POST.getlist("selected_items")

    if not selected_ids:
        return JsonResponse(
            {"ok": False, "error": "No items selected."},
            status=400,
        )

    cart = get_active_cart_for_request(request, create_if_missing=False)
    if not cart:
        return JsonResponse(
            {"ok": False, "error": "Cart not found."},
            status=404,
        )

    items = CartItem.objects.filter(id__in=selected_ids, cart=cart)
    if not items.exists():
        return JsonResponse(
            {"ok": False, "error": "No matching items found."},
            status=404,
        )

    removed_count = items.count()
    items.delete()
    cart.refresh_from_db()

    html = render_to_string("billing/_cart.html",
                            {"cart": cart}, request=request)
    summary_text = f"({cart.items.count()}) – (${cart.total:.2f})"

    messages.success(request, f"Removed {removed_count} service(s) from cart.")
    return JsonResponse(
        {
            "ok": True,
            "html": html,
            "count": cart.items.count(),
            "subtotal": f"{cart.subtotal:.2f}",
            "total": f"{cart.total:.2f}",
            "summary_text": summary_text,
        }
    )


@login_required
@verified_email_required
def live_invoice_view(request, booking_id):
    """
    Loads the current live invoice for a given booking_id.
    Shows the existing services, cancellations, and additions
    before adjustments are finalized.
    """
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)

    payments = PaymentHistory.objects.filter(
        user=request.user,
        service_address=booking.service_address,
    ).order_by("-created_at")

    chain = None

    if payments.exists():
        root = payments.filter(parent__isnull=True).first() or payments.first()

        if hasattr(root, "compute_sections"):
            original_total, add_total, cancel_total, net_total = root.compute_sections()
            chain = {
                "root": root,
                "original_total": original_total,
                "add_total": add_total,
                "cancel_total": cancel_total,
                "net_total": net_total,
                "added": [adj for adj in root.adjustments.all() if adj.amount > 0],
                "cancelled": [adj for adj in root.adjustments.all() if adj.amount < 0],
            }
        else:
            print(f"⚠️ root object has no compute_sections: {root}")
    else:
        print(f"⚠️ No PaymentHistory found for {booking.service_address}")

    return render(
        request,
        "billing/live_invoice.html",
        {
            "booking": booking,
            "chain": chain,
        },
    )


@login_required
@verified_email_required
def live_invoice_view_address(request, address):
    """
    Interactive 'live invoice' view showing all service items, refund eligibility,
    and running totals for a specific property address.
    """
    from urllib.parse import unquote
    from django.utils import timezone
    from billing.utils import get_refund_policy

    address = unquote(address)

    bookings = Booking.objects.filter(
        user=request.user,
        service_address__iexact=address,
    ).order_by("date", "time_slot__label")

    payments = PaymentHistory.objects.filter(
        user=request.user,
        service_address__iexact=address,
    ).order_by("created_at")

    if not bookings.exists() and not payments.exists():
        raise Http404("No invoice data found for this address.")

    bookings_original = bookings.filter(status="Booked")
    bookings_cancelled = bookings.filter(status="Cancelled")

    latest_payment = payments.last()
    if latest_payment:
        bookings_added = bookings.filter(
            created_at__gt=latest_payment.created_at,
            status="Booked",
        )
    else:
        bookings_added = Booking.objects.none()

    def get_booking_dt(booking):
        """
        Build the real booking datetime using the slot start time when possible.
        Falls back to midnight if parsing fails.
        """
        try:
            slot_label = getattr(booking.time_slot, "label", "") or ""
            start_str = slot_label.split("–")[0].split("-")[0].strip()
            start_time = dt.strptime(start_str, "%H:%M").time()
            return timezone.make_aware(
                dt.combine(booking.date, start_time),
                timezone.get_current_timezone(),
            )
        except Exception:
            return timezone.make_aware(
                dt.combine(booking.date, dt.min.time()),
                timezone.get_current_timezone(),
            )

    def get_refund_amount_for_booking(booking):
        """
        Find the latest negative PaymentHistory adjustment linked to this booking.
        Returns a positive display amount like 30.00, or 0.00 if none exists.
        """
        refund_entry = (
            PaymentHistory.objects.filter(
                user=request.user,
                booking=booking,
                amount__lt=0,
            )
            .order_by("-created_at")
            .first()
        )
        if refund_entry:
            return abs(refund_entry.amount)
        return Decimal("0.00")

    def annotate_booking(booking):
        booking_dt = get_booking_dt(booking)
        status, refund_pct = get_refund_policy(booking_dt)

        refund_amount = (
            get_refund_amount_for_booking(booking)
            if booking.status == "Cancelled"
            else Decimal("0.00")
        )

        return {
            "id": booking.id,
            "date": booking.date,
            "service": str(booking.service_category),
            "time_slot": getattr(booking.time_slot, "label", ""),
            "price": float(getattr(booking, "unit_price", 0)),
            "refund_amount": float(refund_amount),
            "status": status if booking.status != "Cancelled" else "Cancelled",
            "refund_pct": refund_pct,
            "is_completed": status == "Locked",
        }

    bookings_original = [annotate_booking(b) for b in bookings_original]
    bookings_cancelled = [annotate_booking(b) for b in bookings_cancelled]
    bookings_added = [annotate_booking(b) for b in bookings_added]

    paid_total = sum(
        payment.amount for payment in payments if payment.amount > 0
    )
    refund_total = abs(
        sum(payment.amount for payment in payments if payment.amount < 0)
    )
    net_total = paid_total - refund_total

    return render(
        request,
        "billing/live_invoice.html",
        {
            "address": address,
            "bookings_original": bookings_original,
            "bookings_cancelled": bookings_cancelled,
            "bookings_added": bookings_added,
            "payments": payments,
            "paid_total": paid_total,
            "refund_total": refund_total,
            "net_total": net_total,
        },
    )


@login_required
@verified_email_required
@require_POST
def cancel_selected_services(request):
    """
    Cancels selected bookings from the live invoice / payment history flow.

    Fixes:
    - Uses the booking's own primary_payment_record first
    - Does NOT fall back to "latest payment for this address"
    - Prevents refunding more than the charge tied to that booking
    - Keeps user-facing messages and refund confirmation email behavior
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY

    selected_ids = request.POST.getlist("selected_bookings")

    if not selected_ids:
        messages.warning(
            request, "No services were selected for cancellation.")
        return redirect("billing:payment_history")

    cancelled_count = 0
    refunded_count = 0
    locked_count = 0

    for booking_id in selected_ids:
        try:
            booking = Booking.objects.select_related(
                "time_slot",
                "primary_payment_record",
                "service_category",
            ).get(
                id=booking_id,
                user=request.user,
            )
        except Booking.DoesNotExist:
            print(
                f"⚠️ Booking {booking_id} not found for {request.user.username}")
            continue

        # Build booking datetime from booking.date + timeslot start time
        booking_dt = None
        try:
            slot_label = getattr(booking.time_slot, "label", "") or ""
            start_str = slot_label.split("–")[0].split("-")[0].strip()
            start_time = dt.strptime(start_str, "%H:%M").time()
            booking_dt = timezone.make_aware(
                dt.combine(booking.date, start_time),
                timezone.get_current_timezone(),
            )
        except Exception:
            booking_dt = timezone.make_aware(
                dt.combine(booking.date, dt.min.time()),
                timezone.get_current_timezone(),
            )

        refund_label, refund_pct = get_refund_policy(booking_dt)

        # ✅ Use the booking's own payment mapping first.
        root_payment = booking.primary_payment_record

        # Fallback 1: explicitly linked root payment for THIS booking
        if not root_payment:
            root_payment = (
                PaymentHistory.objects.filter(
                    user=request.user,
                    linked_bookings=booking,
                    parent__isnull=True,
                )
                .order_by("-created_at")
                .first()
            )

        # Fallback 2: legacy direct booking link only
        if not root_payment:
            root_payment = (
                PaymentHistory.objects.filter(
                    user=request.user,
                    booking=booking,
                    parent__isnull=True,
                )
                .order_by("-created_at")
                .first()
            )

        # ❌ Intentionally NO address-level fallback here.
        if not root_payment:
            print(
                f"⚠️ No root payment record found for booking {booking_id} "
                f"(address fallback intentionally disabled)"
            )
            messages.error(
                request,
                f"Could not determine the original payment for "
                f"{booking.service_category} on {booking.date}.",
            )
            continue

        original_amt = booking.total_amount or Decimal("0.00")
        refund_amt = (
            original_amt * Decimal(refund_pct) / Decimal("100")
        ).quantize(Decimal("0.01"))
        penalty_amt = (original_amt - refund_amt).quantize(Decimal("0.01"))

        # Locked = no refund and do not cancel
        if refund_pct == 0:
            print(
                f"⛔ Booking {booking.id} is locked; no cancellation allowed.")
            locked_count += 1
            messages.warning(
                request,
                f"{booking.service_category} on {booking.date} can no longer be cancelled.",
            )
            continue

        refund_status = "Cancelled"

        try:
            # Defensive guard: never attempt to refund more than the charge
            charge_amount = root_payment.amount or Decimal("0.00")
            if refund_amt > charge_amount:
                print(
                    f"⚠️ Refund amount exceeds charge for booking {booking.id}: "
                    f"refund_amt={refund_amt}, charge_amount={charge_amount}, "
                    f"root_payment_id={root_payment.id}, "
                    f"stripe_payment_id={root_payment.stripe_payment_id}"
                )
                messages.error(
                    request,
                    f"Refund failed for {booking.service_category} on {booking.date}: "
                    "refund exceeds original charge."
                )
                continue

            # Only talk to Stripe if there is money to refund
            if refund_amt > 0 and root_payment.stripe_payment_id:
                stripe.Refund.create(
                    payment_intent=root_payment.stripe_payment_id,
                    amount=int(refund_amt * 100),
                )
                refund_status = "Refunded"
                refunded_count += 1
                print(
                    f"💸 Stripe refund successful for booking {booking.id}: "
                    f"${refund_amt} ({refund_pct}% refund) via root payment #{root_payment.id}"
                )
            else:
                print(
                    f"⚠️ No Stripe refund issued for booking {booking.id}. "
                    f"refund_amt={refund_amt}, "
                    f"stripe_payment_id={root_payment.stripe_payment_id}"
                )

            if refund_pct == 100:
                note = "Service cancelled and fully refunded"
            elif refund_pct == 50:
                note = (
                    "Late cancellation inside 72 hours: 50% refunded, "
                    f"50% penalty retained (${penalty_amt:.2f})"
                )
            else:
                note = "Service cancelled"

            refund_entry = PaymentHistory.objects.create(
                user=request.user,
                parent=root_payment,
                booking=booking,
                amount=-refund_amt,
                adjustments_total_amt=Decimal("0.00"),
                status=refund_status,
                notes=note,
                service_address=booking.service_address,
            )

            booking.status = "Cancelled"
            booking.save(update_fields=["status"])
            cancelled_count += 1

            print(
                f"✅ Booking {booking.id} cancelled — "
                f"Refund record #{refund_entry.id} "
                f"(${refund_amt:.2f}, {refund_pct}%)"
            )

            try:
                from billing.utils import send_refund_confirmation_email
                send_refund_confirmation_email(request.user, refund_entry)
            except Exception as e:
                print(f"⚠️ Refund email failed: {e}")

        except Exception as e:
            print(f"❌ Refund failed for booking {booking_id}: {e}")
            messages.error(
                request,
                f"Refund failed for {booking.service_category} on {booking.date}.",
            )

    if cancelled_count:
        messages.success(
            request,
            f"{cancelled_count} service(s) cancelled. "
            f"{refunded_count} refund(s) processed."
        )

    if locked_count:
        messages.warning(
            request,
            f"{locked_count} service(s) were inside the non-cancellable window."
        )

    return redirect(reverse("billing:payment_history") + f"?t={now().timestamp()}")


@login_required
@verified_email_required
@require_POST
def add_service_adjustment(request):
    """
    Adds or removes a service adjustment for an existing booking.
    - Positive = additional charge
    - Negative = refund
    - Always recorded in PaymentHistory and linked to the booking
    - Works in Stripe sandbox mode (no live account needed)
    """
    booking_id = request.POST.get("booking_id")
    delta_amount = Decimal(request.POST.get("delta_amount") or "0.00")
    note = (request.POST.get("note") or "Service adjustment").strip()

    if not booking_id:
        return JsonResponse({"ok": False, "error": "No booking selected."})

    booking = Booking.objects.filter(id=booking_id, user=request.user).first()
    if not booking:
        return JsonResponse({"ok": False, "error": "Booking not found."})
    if delta_amount == 0:
        return JsonResponse({"ok": False, "error": "Adjustment amount cannot be zero."})

    stripe_charge = None
    stripe_refund = None
    stripe_error = None

    try:
        if delta_amount > 0:
            payment_intent = stripe.PaymentIntent.create(
                amount=int(delta_amount * 100),
                currency="USD",
                automatic_payment_methods={"enabled": True},
                metadata={"booking_id": booking.id, "type": "ADJUSTMENT"},
            )
            stripe_charge = payment_intent.id
        else:
            last_payment = (
                PaymentHistory.objects.filter(
                    linked_bookings=booking, amount__gt=0)
                .order_by("-created_at")
                .first()
            )
            if last_payment and last_payment.raw_data.get("payment_intent_id"):
                stripe_refund = stripe.Refund.create(
                    payment_intent=last_payment.raw_data.get(
                        "payment_intent_id"),
                    amount=int(abs(delta_amount) * 100),
                )
    except stripe.error.StripeError as e:
        stripe_error = str(e)

    with transaction.atomic():
        adj_entry = PaymentHistory.objects.create(
            user=request.user,
            amount=delta_amount,
            currency="USD",
            service_address=booking.service_address,
            created_at=now(),
            status="Paid" if delta_amount > 0 else "Refunded",
            payment_type="ADJUSTMENT",
            notes=f"{note} — {'Billed' if delta_amount > 0 else 'Refunded'} via adjustment.",
            raw_data={
                "stripe_payment_intent": stripe_charge,
                "stripe_refund_id": getattr(stripe_refund, "id", None),
                "stripe_error": stripe_error,
                "delta_amount": f"{delta_amount:.2f}",
            },
        )
        adj_entry.linked_bookings.add(booking)
        booking.total_amount += delta_amount
        booking.save(update_fields=["total_amount", "updated_at"])

    summary = (
        f"Service {'added' if delta_amount > 0 else 'removed'} successfully. "
        f"{'Charge simulated' if delta_amount > 0 else 'Refund simulated'} in sandbox mode."
    )

    return JsonResponse({"ok": True, "summary": summary, "delta": float(delta_amount)})


@login_required
@verified_email_required
@require_POST
def submit_adjustment(request):
    """
    Handles modal submission for Add / Remove Service.
    Creates a child PaymentHistory under the selected root,
    updates totals, and redirects to checkout if payment required.
    """
    parent_id = request.POST.get("parent_id")
    booking_id = request.POST.get("booking_id")
    delta_amount = request.POST.get("delta_amount")
    note = request.POST.get("note", "")

    if not (parent_id and booking_id and delta_amount):
        return JsonResponse({"ok": False, "error": "Missing required fields."})

    try:
        parent = PaymentHistory.objects.get(pk=parent_id, user=request.user)
        booking = Booking.objects.get(pk=booking_id, user=request.user)
        delta = Decimal(delta_amount)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"Invalid selection: {e}"})

    PaymentHistory.objects.create(
        user=request.user,
        parent=parent,
        service_address=booking.service_address,
        amount=delta,
        currency=parent.currency,
        status="Adjustment",
        notes=note,
    )
    parent.refresh_from_db()

    if delta > 0:
        message = f"Additional service (${delta}) added. Proceed to checkout."
        next_step = reverse("billing:checkout")
    elif delta < 0:
        message = f"Refund of ${abs(delta)} initiated."
        next_step = reverse("billing:payment_history")
    else:
        message = "No change."
        next_step = reverse("billing:payment_history")

    return JsonResponse(
        {
            "ok": True,
            "message": message,
            "redirect": next_step,
        }
    )


@login_required_json
@require_POST
def cart_clear(request):
    cart = _get_or_create_cart(request)
    cart.items.all().delete()
    return JsonResponse(
        {
            "ok": True,
            "html": render_to_string("billing/_cart.html", {"cart": cart}, request=request),
            "count": 0,
            "total": "0.00",
            "summary_text": f"({cart.items.count()}) – (${cart.total:.2f})",
        }
    )


@login_required
def cart_detail(request):
    """Optional full-page cart view (non-AJAX)."""
    cart = _get_or_create_cart(request)
    get_token(request)
    return render(request, "billing/_cart.html", {"cart": cart})


@login_required
@verified_email_required
def payment_success(request):
    """
    Finalizes a successful Stripe checkout safely and idempotently.

    Defensive validation:
    - blocks missing/invalid session_id
    - blocks re-processing the same payment if cart is already gone
    - blocks past-dated cart items
    - blocks duplicate booking creation across ALL active bookings,
      not just bookings already linked to the current payment record
    """
    from billing.utils import get_active_cart_for_request

    session_id = request.GET.get("session_id")
    if not session_id:
        messages.error(request, "Missing Stripe session ID.")
        return redirect("billing:checkout")

    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        print(f"❌ Stripe session retrieval error: {e}")
        messages.error(request, "Could not verify your payment session.")
        return redirect("billing:checkout")

    payment_status = getattr(checkout_session, "payment_status", None)
    if payment_status != "paid":
        messages.error(
            request,
            "Payment was not completed successfully.",
        )
        return redirect("billing:checkout")

    metadata = getattr(checkout_session, "metadata", {}) or {}
    payment_intent_id = getattr(checkout_session, "payment_intent", None)

    cart = None
    cart_id = metadata.get("cart_id") or request.session.get("cart_id")

    if cart_id:
        cart = Cart.objects.filter(
            id=cart_id,
            user=request.user,
        ).prefetch_related("items").first()

    if not cart:
        cart = get_active_cart_for_request(request, create_if_missing=False)

    # Idempotent path: if cart is gone but payment already exists, do not fail.
    if not cart or not cart.items.exists():
        existing_payment = PaymentHistory.objects.filter(
            user=request.user,
            stripe_payment_id=payment_intent_id,
            parent__isnull=True,
        ).first()

        if existing_payment:
            messages.success(
                request,
                "Payment already processed. Showing your payment history.",
            )
            return redirect("billing:payment_history")

        messages.error(request, "Your cart is empty or expired.")
        return redirect("billing:checkout")

    if _cart_has_past_dates(cart):
        messages.error(
            request,
            "Past dates cannot be booked. Please rebuild your cart with present or future dates only.",
        )
        return redirect("billing:checkout")

    service_address = (
        (metadata.get("service_address") or "").strip()
        or getattr(cart, "address_key", None)
        or request.session.get("customer_address")
        or request.session.get("service_address")
        or "Unknown"
    ).strip()

    payment_record = PaymentHistory.objects.filter(
        user=request.user,
        stripe_payment_id=payment_intent_id,
        parent__isnull=True,
    ).first()

    created_root_payment = False
    created_bookings = []

    try:
        if not payment_record:
            payment_record = PaymentHistory.objects.create(
                user=request.user,
                amount=cart.total,
                adjustments_total_amt=Decimal("0.00"),
                currency="USD",
                status="Paid",
                service_address=service_address,
                notes="Stripe Checkout Payment",
                payment_type="Stripe Checkout",
                stripe_payment_id=payment_intent_id,
            )
            created_root_payment = True
        else:
            fields_to_update = []

            if payment_record.amount != cart.total:
                payment_record.amount = cart.total
                fields_to_update.append("amount")

            if getattr(payment_record, "currency", None) != "USD":
                payment_record.currency = "USD"
                fields_to_update.append("currency")

            if payment_record.status != "Paid":
                payment_record.status = "Paid"
                fields_to_update.append("status")

            if payment_record.service_address != service_address:
                payment_record.service_address = service_address
                fields_to_update.append("service_address")

            if getattr(payment_record, "payment_type", "") != "Stripe Checkout":
                payment_record.payment_type = "Stripe Checkout"
                fields_to_update.append("payment_type")

            if not payment_record.notes:
                payment_record.notes = "Stripe Checkout Payment"
                fields_to_update.append("notes")

            if fields_to_update:
                payment_record.save(update_fields=fields_to_update)

        existing_booking_keys = set(
            Booking.objects.filter(
                primary_payment_record=payment_record
            ).values_list(
                "service_category_id",
                "employee_id",
                "date",
                "time_slot_id",
            )
        )

        today = timezone.localdate()

        for item in cart.items.all():
            if item.date < today:
                messages.error(
                    request,
                    "Past dates cannot be booked. Please rebuild your cart and try again.",
                )
                return redirect("billing:checkout")

            booking_key = (
                item.service_category_id,
                item.employee_id,
                item.date,
                item.time_slot_id,
            )

            # Idempotent guard for this same payment record
            if booking_key in existing_booking_keys:
                continue

            # FINAL SERVER-SIDE DUPLICATE / SLOT-CONFLICT GUARD
            # Checks ALL active bookings, not just current payment_record.
            conflicting_booking = Booking.objects.filter(
                employee_id=item.employee_id,
                date=item.date,
                time_slot_id=item.time_slot_id,
            ).exclude(
                status__iexact="Cancelled"
            ).first()

            if conflicting_booking:
                messages.error(
                    request,
                    (
                        f"Sorry, {item.employee} is no longer available for "
                        f"{item.date} at {item.time_slot}. Please search again."
                    ),
                )
                return redirect("scheduling:search_by_date")

            booking = Booking.objects.create(
                user=request.user,
                service_address=service_address,
                service_category=item.service_category,
                employee=item.employee,
                date=item.date,
                time_slot=item.time_slot,
                unit_price=item.unit_price,
                total_amount=item.subtotal,
                status="Booked",
                primary_payment_record=payment_record,
            )
            created_bookings.append(booking)
            existing_booking_keys.add(booking_key)

        if created_bookings:
            payment_record.linked_bookings.add(*created_bookings)
            payment_record.save()

        paid_cart_id = cart.id
        paid_address_key = (cart.address_key or "").strip()

        cart.items.all().delete()
        cart.delete()

        stale_carts = Cart.objects.filter(
            user=request.user
        ).exclude(id=paid_cart_id)

        if paid_address_key:
            stale_carts = stale_carts.filter(
                models.Q(address_key__iexact=paid_address_key)
                | models.Q(address_key__isnull=True)
                | models.Q(address_key__exact="")
            )

        for stale_cart in stale_carts:
            stale_cart.items.all().delete()
            stale_cart.delete()

        request.session.pop("cart_id", None)
        request.session.pop("last_checkout_session_id", None)
        request.session.modified = True

        if created_root_payment or created_bookings:
            try:
                all_bookings = list(
                    Booking.objects.filter(
                        primary_payment_record=payment_record
                    )
                    .select_related("service_category", "time_slot", "employee")
                    .order_by("date", "time_slot__label")
                )
                send_payment_receipt_email(
                    request.user, payment_record, all_bookings, request
                )
                print(f"📧 Sent receipt to {request.user.email}")
            except Exception as e:
                print(f"⚠️ Payment receipt email failed: {e}")

            messages.success(
                request, "Payment successful! Your booking has been confirmed."
            )
        else:
            messages.success(
                request,
                "Payment was already processed. Showing your payment history.",
            )

        return redirect("billing:payment_history")

    except Exception as e:
        print(f"❌ Payment success error: {e}")
        messages.error(request, f"Payment processing error: {e}")
        return redirect("billing:checkout")


@login_required
@verified_email_required
def payment_history(request):
    """
    Groups all PaymentHistory records by root transaction and includes
    the actual booked service dates tied to that payment.
    """
    user = request.user

    roots = (
        PaymentHistory.objects.filter(user=user, parent__isnull=True)
        .order_by("-created_at")
    )

    cards = []

    for root in roots:
        related_entries = PaymentHistory.objects.filter(
            models.Q(id=root.id) | models.Q(parent=root)
        ).order_by("created_at")

        related_bookings = (
            Booking.objects.filter(primary_payment_record=root)
            .select_related("service_category", "time_slot", "employee")
            .order_by("date", "time_slot__label")
        )

        original_total, add_total, cancel_total, net_total = root.compute_sections()

        cards.append(
            {
                "address": root.service_address,
                "stripe_payment_id": root.stripe_payment_id or "N/A",
                "root": root,
                "entries": related_entries,
                "bookings": related_bookings,
                "original_total": original_total,
                "add_total": add_total,
                "cancel_total": cancel_total,
                "net_total": net_total,
                "added": root.adjustments.filter(amount__gt=0),
                "cancelled": root.adjustments.filter(amount__lt=0),
            }
        )

    print(
        f"DEBUG: Found {len(cards)} grouped property cards for {user.username}")
    return render(request, "billing/payment_history.html", {"cards": cards})
