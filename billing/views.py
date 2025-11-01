"""
billing/views.py
Handles checkout, Stripe integration, payment tracking, and admin management.
"""
from io import BytesIO
from scheduling.models import Booking
from billing.models import PaymentHistory
from django.utils.timezone import now
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import datetime
# from datetime import datetime as dt, timedelta
import json
from decimal import Decimal
import stripe

from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from django.utils.timezone import now, localdate
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token
from django.http import JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Sum
from django.http import FileResponse
from django.urls import reverse

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.enums import TA_RIGHT, TA_LEFT

from billing.utils.email_helpers import send_payment_receipt_email
from customers.models import RegisteredCustomer
from scheduling.models import Employee, TimeSlot, ServiceCategory, Booking
from .utils import _get_or_create_cart, get_service_address, lock_service_address, normalize_address, get_active_cart_for_request
from .models import Payment
from .constants import SERVICE_PRICES, SALES_TAX_RATE
from .forms import CheckoutForm
from .models import Cart, CartItem, CartManager, PaymentHistory
# ----------------------------------------------------------------------
# ⚙️ Stripe Setup
# ----------------------------------------------------------------------
stripe.api_key = settings.STRIPE_SECRET_KEY


PENALTY_WINDOW_HOURS = 72


# def _refresh_booking_statuses_for_user(user):
#     """
#     Mark bookings Completed if in the past (and not already Cancelled).
#     Leave Booked for future. This runs whenever we render history or on success.
#     """
#     today = localdate()
#     qs = Booking.objects.filter(user=user).exclude(status="Cancelled")
#     for b in qs:
#         if b.date < today and b.status != "Completed":
#             b.status = "Completed"
#             b.save(update_fields=["status"])


def _penalty_applies(booking: Booking) -> bool:
    """True if within 72h window from now."""
    # if you have a concrete datetime, use it; else fallback to date-at-midnight logic
    start_dt = getattr(booking, "datetime_start", None)
    if start_dt:
        hours = (start_dt - now()).total_seconds() / 3600.0
    else:
        # date based approximation
        hours = (booking.date - localdate()).days * 24.0
    return hours < PENALTY_WINDOW_HOURS

# ----------------------------------------------------------------------
# 🏁 Simple Checkout Page (called by navbar burger)
# ----------------------------------------------------------------------


@login_required
def checkout(request):
    """
    Displays the user's cart summary and recalculates totals before Stripe checkout.
    Allows items to be removed (via AJAX or via 'Remove Selected' checkboxes).
    """
    from billing.models import Cart, CartItem
    from decimal import Decimal

    cart = (
        Cart.objects.filter(user=request.user)
        .prefetch_related("items__service_category", "items__employee", "items__time_slot")
        .first()
    )

    if not cart or not cart.items.exists():
        messages.info(
            request, "Your cart is empty — please add services before checkout.")
        return redirect("scheduling:search_by_time_slot")

    # 🧾 Dynamic removal support if JS posted any selected_items
    if request.method == "POST" and "selected_items" in request.POST:
        ids_to_remove = request.POST.getlist("selected_items")
        if ids_to_remove:
            CartItem.objects.filter(cart=cart, id__in=ids_to_remove).delete()
            cart.refresh_from_db()
            messages.success(
                request, f"Removed {len(ids_to_remove)} item(s) from your cart.")
            return redirect("billing:checkout")

    # 🧮 Recalculate totals
    subtotal = Decimal("0.00")
    for item in cart.items.all():
        subtotal += item.unit_price or Decimal("0.00")

    TAX_RATE = Decimal(getattr(settings, "SALES_TAX_RATE", 0.0825))
    subtotal = sum((item.unit_price or Decimal("0.00"))
                   for item in cart.items.all())
    TAX_RATE = Decimal(getattr(settings, "SALES_TAX_RATE", 0.0825))
    tax = (subtotal * TAX_RATE).quantize(Decimal("0.01"))
    total = (subtotal + tax).quantize(Decimal("0.01"))

    context = {
        "cart": cart,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "SALES_TAX_RATE": TAX_RATE,
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
    from decimal import Decimal
    import stripe
    from django.urls import reverse
    from django.conf import settings
    from .models import Cart

    stripe.api_key = settings.STRIPE_SECRET_KEY

    cart = _get_or_create_cart(request)
    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("billing:checkout")

    # Totals (authoritative for our metadata display on success)
    subtotal = cart.subtotal
    tax = cart.tax
    total = cart.total
    service_address = request.session.get("service_address", "")

    # Build absolute URLs for Stripe redirect
    success_url = (
        request.build_absolute_uri(reverse("billing:payment_success"))
        + "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = request.build_absolute_uri(reverse("billing:checkout"))

    try:
        # Minimal line item to charge the full total:
        # (You can switch back to per-item line_items if you prefer.)
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Home services booking"},
                    "unit_amount": int(total * Decimal("100")),
                },
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "subtotal": f"{subtotal:.2f}",
                "tax": f"{tax:.2f}",
                "total": f"{total:.2f}",
                "service_address": service_address,
                "cart_id": str(cart.pk),
                "user_id": str(request.user.id),
            },
        )
        # Optional: store the session id on the cart for traceability
        request.session["last_checkout_session_id"] = checkout_session.id
        request.session.modified = True

        return redirect(checkout_session.url, code=303)

    except Exception as e:
        # Avoid printing emojis (Windows console encoding)
        print("Stripe create session error:", e)
        messages.error(request, f"Could not start checkout: {e}")
        return redirect("billing:checkout")


# ----------------------------------------------------------------------
# ✅ Payment Success / Cancel
# ----------------------------------------------------------------------


@login_required
def payment_cancel(request):
    """Handles user cancellation from Stripe checkout."""
    messages.info(
        request, "Your payment was cancelled — no charges were made.")
    return redirect("billing:checkout")


# ----------------------------------------------------------------------
# 🧾 Payment History (user)
# ----------------------------------------------------------------------


# Optional helper to refresh booking statuses based on current date

def _refresh_booking_statuses_for_user(user):
    """Auto-refresh status for user's bookings (Completed / Active)."""
    today = now().date()
    bookings = Booking.objects.filter(user=user)
    for b in bookings:
        if b.date < today and b.status != "Completed":
            b.status = "Completed"
            b.save(update_fields=["status"])
        elif b.date >= today and b.status == "Completed":
            b.status = "Booked"
            b.save(update_fields=["status"])


# ----------------------------------------------------------------------
# 🧾 All Payments (admin)
# ----------------------------------------------------------------------
@login_required
def download_receipt_pdf(request, pk):
    """Generate a detailed PDF receipt with grouped adjustments."""
    root = get_object_or_404(
        PaymentHistory, id=pk, user=request.user, parent__isnull=True
    )
    chain = root.compute_sections()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=0.75 * inch,
                            rightMargin=0.75 * inch,
                            topMargin=0.75 * inch,
                            bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph(
        "<b>Tucker & Dale’s Home Services</b>", styles["Title"]
    ))
    elements.append(Paragraph(
        f"Receipt generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 0.25 * inch))

    # Customer + service info
    elements.append(
        Paragraph(f"<b>Service Address:</b> {root.service_address}", styles["Normal"]))
    elements.append(Paragraph(
        f"<b>Transaction ID:</b> {root.stripe_payment_id or 'N/A'}", styles["Normal"]))
    elements.append(
        Paragraph(f"<b>Status:</b> {root.status}", styles["Normal"]))
    elements.append(Spacer(1, 0.25 * inch))

    def make_table(title, rows, color):
        """Utility to create styled tables for each section."""
        elements.append(Paragraph(f"<b>{title}</b>", styles["Heading4"]))
        data = [["Date", "Description", "Amount (USD)"]] + rows
        tbl = Table(data, colWidths=[1.5 * inch, 3.5 * inch, 1.5 * inch])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        elements.append(tbl)
        elements.append(Spacer(1, 0.15 * inch))

    # ✅ Original Services
    make_table(
        "Original Services",
        [[root.created_at.strftime("%Y-%m-%d"),
          root.notes or "Initial Booking Payment",
          f"${root.amount:.2f}"]],
        colors.green
    )

    # ❌ Cancellations
    cancelled = [a for a in root.adjustments.all() if a.amount < 0]
    if cancelled:
        rows = [[a.created_at.strftime("%Y-%m-%d"),
                 a.notes or "Refund / Penalty",
                 f"-${abs(a.amount):.2f}"] for a in cancelled]
        make_table("Cancellations / Refunds", rows, colors.red)

    # ➕ Additions
    added = [a for a in root.adjustments.all() if a.amount > 0]
    if added:
        rows = [[a.created_at.strftime("%Y-%m-%d"),
                 a.notes or "Additional Service",
                 f"+${a.amount:.2f}"] for a in added]
        make_table("Added Services", rows, colors.blue)

    # 🧮 Totals
    o, a, c, net = root.compute_sections()
    totals_data = [
        ["Original Total:", f"${o:.2f}"],
        ["Added Services:", f"+${a:.2f}"],
        ["Refunds / Penalties:", f"-${abs(c):.2f}"],
        ["Final Adjusted Total:", f"${net:.2f}"],
    ]
    totals_tbl = Table(totals_data, colWidths=[3.5 * inch, 3.5 * inch])
    totals_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
    ]))
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(totals_tbl)

    doc.build(elements)
    buffer.seek(0)
    filename = f"Receipt_{root.service_address.replace(' ', '_')}_{root.created_at.date()}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
def download_yearly_summary_pdf(request):
    """
    Generate a combined summary PDF of all PaymentHistory chains
    for this user, grouped by service_address.
    Useful for landlords/property managers tracking multiple sites.
    """
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from django.utils import timezone

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=0.75 * inch,
                            rightMargin=0.75 * inch,
                            topMargin=0.75 * inch,
                            bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = []

    # 🧭 Header
    elements.append(
        Paragraph("<b>Tucker & Dale’s Home Services</b>", styles["Title"]))
    elements.append(
        Paragraph(f"Annual Summary for {request.user.username}", styles["Normal"]))
    elements.append(Paragraph(
        f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))

    # 🏘️ Group PaymentHistory roots by service_address
    roots = (
        PaymentHistory.objects
        .filter(user=request.user, parent__isnull=True)
        .select_related("user")
        .order_by("service_address", "-created_at")
    )
    grouped = {}
    for root in roots:
        grouped.setdefault(root.service_address, []).append(root)

    grand_total = Decimal("0.00")

    # 🧾 Iterate properties
    for addr, chains in grouped.items():
        elements.append(Paragraph(f"<b>🏠 {addr}</b>", styles["Heading2"]))
        elements.append(Spacer(1, 0.1 * inch))

        prop_total = Decimal("0.00")

        for root in chains:
            o, a, c, net = root.compute_sections()
            prop_total += net

            data = [
                ["Date", "Original", "Added", "Refunded", "Adjusted Total"],
                [
                    root.created_at.strftime("%Y-%m-%d"),
                    f"${o:.2f}",
                    f"+${a:.2f}" if a > 0 else "$0.00",
                    f"-${abs(c):.2f}" if c else "$0.00",
                    f"${net:.2f}",
                ],
            ]
            t = Table(data, colWidths=[
                      1.3 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.1 * inch))

        # Property subtotal
        elements.append(Paragraph(
            f"<b>Total for {addr}:</b> ${prop_total:.2f}",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 0.3 * inch))
        grand_total += prop_total

    # 🧮 Grand total
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(
        Paragraph("<b>Grand Total Across All Properties</b>", styles["Heading3"]))
    elements.append(Paragraph(f"<b>${grand_total:.2f}</b>", styles["Title"]))
    elements.append(Spacer(1, 0.3 * inch))

    doc.build(elements)
    buffer.seek(0)

    filename = f"Yearly_Summary_{request.user.username}_{timezone.now().year}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


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
@require_POST
def stripe_webhook(request):
    """
    Handles Stripe 'payment_intent.succeeded' events.
    Records payment details in PaymentHistory for user reference.
    """
    import stripe
    from billing.models import PaymentHistory, Cart
    from django.contrib.auth.models import User

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponseBadRequest("Invalid payload or signature")

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        payment_id = intent.get("id")
        amount = Decimal(intent.get("amount_received", 0)) / 100
        metadata = intent.get("metadata", {})

        user_id = metadata.get("user_id")
        cart_id = metadata.get("cart_id")

        # Retrieve user and cart if available
        user = User.objects.filter(id=user_id).first()
        cart = Cart.objects.filter(id=cart_id).first() if cart_id else None

        if user:
            PaymentHistory.objects.create(
                user=user,
                cart=cart,
                stripe_payment_id=payment_id,
                amount=amount,
                service_address=metadata.get("service_address", ""),
                raw_data=intent,
            )
            print(
                f"💾 Saved payment record for {user.username} (${amount:.2f})")

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
    html = render_to_string("billing/_cart.html",
                            {"cart": cart}, request=request)
    summary_text = f"({cart.items.count()}) - (${cart.total:.2f})"

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
    html = render_to_string("billing/_cart.html",
                            {"cart": cart}, request=request)
    return JsonResponse({"ok": True,
                         "html": render_to_string("billing/_cart.html", {"cart": cart}, request=request),
                         "total": str(cart.total),
                         "summary_text": f"({cart.items.count()}) – (${cart.total:.2f})"})


@login_required
@require_POST
def remove_selected_from_cart(request):
    """
    Removes selected cart items and any linked scheduling records.
    Triggered by 'Remove Selected' button in _cart.html.
    """
    selected_ids = request.POST.getlist("selected_items")

    if not selected_ids:
        return JsonResponse({"ok": False, "error": "No items selected."})

    cart = Cart.objects.filter(user=request.user).first()
    if not cart:
        return JsonResponse({"ok": False, "error": "Cart not found."})

    items = CartItem.objects.filter(id__in=selected_ids, cart=cart)
    if not items.exists():
        return JsonResponse({"ok": False, "error": "No matching items found."})

    # --- Remove associated bookings if they exist ---
    removed_count = 0
    for item in items:
        Booking.objects.filter(cart_item=item).delete()
        removed_count += 1
    items.delete()

    # --- Recalculate totals and rebuild cart HTML ---
    cart.refresh_from_db()

    html = render_to_string("billing/_cart.html",
                            {"cart": cart}, request=request)
    summary_text = f"{cart.items.count} item{'s' if cart.items.count != 1 else ''} in cart"

    messages.success(request, f"Removed {removed_count} service(s) from cart.")
    return JsonResponse({"ok": True, "html": html, "summary_text": summary_text})


@login_required
def live_invoice_view(request, booking_id):
    """
    Loads the current live invoice for a given booking_id.
    Shows the existing services, cancellations, and additions
    before adjustments are finalized.
    """
    from scheduling.models import Booking
    booking = get_object_or_404(Booking, pk=booking_id)

    # Related payments for this user + service address
    payments = PaymentHistory.objects.filter(
        user=request.user,
        service_address=booking.service_address
    ).order_by("-created_at")

    # Initialize variables safely
    chain = None
    root = None

    if payments.exists():
        # Try to find the root; fallback to most recent payment
        root = payments.filter(parent__isnull=True).first() or payments.first()

        # Defensive check before computing
        if hasattr(root, "compute_sections"):
            original_total, add_total, cancel_total, net_total = root.compute_sections()
            chain = {
                "root": root,
                "original_total": original_total,
                "add_total": add_total,
                "cancel_total": cancel_total,
                "net_total": net_total,
                "added": [a for a in root.adjustments.all() if a.amount > 0],
                "cancelled": [a for a in root.adjustments.all() if a.amount < 0],
            }
        else:
            print(f"⚠️ root object has no compute_sections: {root}")
    else:
        print(f"⚠️ No PaymentHistory found for {booking.service_address}")

    return render(request, "billing/live_invoice.html", {
        "booking": booking,
        "chain": chain,
    })


@login_required
def live_invoice_view_address(request, address):
    """
    Interactive 'live invoice' view showing all service items, refund eligibility,
    and running totals for a specific property address.
    Divides items into Original bookings, Cancellations (refunds), and Added services.
    """
    from urllib.parse import unquote
    from datetime import datetime
    from django.utils import timezone
    from scheduling.models import Booking
    from billing.utils import get_refund_policy

    address = unquote(address)

    # ✅ Fetch all bookings for this address and user
    bookings = Booking.objects.filter(
        user=request.user,
        service_address__iexact=address
    ).order_by("date", "time_slot__label")

    # ✅ Fetch all related payments
    payments = PaymentHistory.objects.filter(
        user=request.user,
        service_address__iexact=address
    ).order_by("created_at")

    # ✅ Sectionize bookings
    bookings_original = bookings.filter(status="Booked")
    bookings_cancelled = bookings.filter(status="Cancelled")
    # Heuristic for "added" (later-created bookings that aren’t cancellations)
    latest_payment = payments.last()
    if latest_payment:
        bookings_added = bookings.filter(
            created_at__gt=latest_payment.created_at, status="Booked")
    else:
        bookings_added = Booking.objects.none()

    # ✅ Compute refund eligibility and completion status
    today = timezone.now().date()

    def annotate_booking(b):
        status, refund_pct = get_refund_policy(
            datetime.combine(b.date, datetime.min.time(),
                             tzinfo=timezone.get_current_timezone())
        )
        return {
            "id": b.id,
            "date": b.date,
            "service": str(b.service_category),
            "time_slot": getattr(b.time_slot, "label", ""),
            "price": float(getattr(b, "unit_price", 0)),
            "status": status,
            "refund_pct": refund_pct,
            "is_completed": status == "Locked",
        }

    bookings_original = [annotate_booking(b) for b in bookings_original]
    bookings_cancelled = [annotate_booking(b) for b in bookings_cancelled]
    bookings_added = [annotate_booking(b) for b in bookings_added]

    # ✅ Totals
    paid_total = sum(p.amount for p in payments if p.amount > 0)
    refund_total = abs(sum(p.amount for p in payments if p.amount < 0))
    net_total = paid_total - refund_total

    # ✅ Render structured context
    return render(request, "billing/live_invoice.html", {
        "address": address,
        "bookings_original": bookings_original,
        "bookings_cancelled": bookings_cancelled,
        "bookings_added": bookings_added,
        "payments": payments,
        "paid_total": paid_total,
        "refund_total": refund_total,
        "net_total": net_total,
    })


@login_required
@require_POST
def cancel_selected_services(request):
    """
    Process batch cancellation requests with refund percentage per booking.
    """
    booking_ids = request.POST.getlist("selected_bookings")
    if not booking_ids:
        return JsonResponse({"error": "No bookings selected."})

    from scheduling.models import Booking
    from billing.models import PaymentHistory
    from billing.utils import get_refund_policy

    total_refund = Decimal("0.00")
    notes = []

    for bid in booking_ids:
        try:
            booking = Booking.objects.get(id=bid, customer__user=request.user)
            price = Decimal(getattr(booking, "price", 0))
            status, pct = get_refund_policy(
                datetime.datetime.combine(booking.date, datetime.datetime.min.time()))
            if pct > 0:
                refund_amt = (price * Decimal(pct) / Decimal(100)
                              ).quantize(Decimal("0.01"))
                total_refund += refund_amt
                PaymentHistory.objects.create(
                    user=request.user,
                    service_address=booking.service_address,
                    amount=-refund_amt,
                    notes=f"{status} refund ({pct}%) for {booking.service_category}",
                    status="Refunded",
                )
                notes.append(
                    f"{booking.service_category} on {booking.date} → {pct}% refund = ${refund_amt}")
                booking.delete()
            else:
                notes.append(
                    f"{booking.service_category} on {booking.date} → No refund (locked)")
        except Booking.DoesNotExist:
            notes.append(f"Booking #{bid} not found.")

    return JsonResponse({
        "ok": True,
        "message": f"Processed {len(booking_ids)} cancellations.\nTotal refund: ${total_refund}\n\n" + "\n".join(notes)
    })


@login_required
@require_POST
def add_service_adjustment(request):
    """
    Adds or removes a service adjustment for an existing booking.
    - Positive = additional charge
    - Negative = refund
    - Always recorded in PaymentHistory and linked to the booking
    - Works in Stripe sandbox mode (no live account needed)
    """
    from decimal import Decimal
    import stripe
    from django.utils.timezone import now
    from django.db import transaction
    from billing.models import PaymentHistory
    from scheduling.models import Booking

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
            # Simulated additional charge
            payment_intent = stripe.PaymentIntent.create(
                amount=int(delta_amount * 100),
                currency="usd",
                automatic_payment_methods={"enabled": True},
                metadata={"booking_id": booking.id, "type": "ADJUSTMENT"},
            )
            stripe_charge = payment_intent.id
        else:
            # Simulated refund (sandbox)
            last_payment = booking.payments.filter(amount__gt=0).first()
            if last_payment and last_payment.raw_data.get("payment_intent_id"):
                stripe_refund = stripe.Refund.create(
                    payment_intent=last_payment.raw_data.get(
                        "payment_intent_id"),
                    amount=int(abs(delta_amount) * 100),
                )
    except stripe.error.StripeError as e:
        stripe_error = str(e)

    # --- Record adjustment ---
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
        booking.payments.add(adj_entry)
        booking.total_amount += delta_amount
        booking.save(update_fields=["total_amount", "updated_at"])

    summary = (
        f"Service {'added' if delta_amount > 0 else 'removed'} successfully. "
        f"{'Charge simulated' if delta_amount > 0 else 'Refund simulated'} in sandbox mode."
    )

    return JsonResponse({"ok": True, "summary": summary, "delta": float(delta_amount)})


@login_required
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

    # Create child adjustment
    child = PaymentHistory.objects.create(
        user=request.user,
        parent=parent,
        service_address=booking.service_address,
        amount=delta,
        currency=parent.currency,
        status="Adjustment",
        notes=note,
    )
    parent.refresh_from_db()

    # Determine payment direction
    if delta > 0:
        message = f"Additional service (${delta}) added. Proceed to checkout."
        next_step = reverse("billing:checkout")
    elif delta < 0:
        message = f"Refund of ${abs(delta)} initiated."
        next_step = reverse("billing:payment_history")
    else:
        message = "No change."

    return JsonResponse({
        "ok": True,
        "message": message,
        "redirect": next_step,
    })


@require_POST
def cart_clear(request):
    cart = _get_or_create_cart(request)
    cart.items.all().delete()
    html = render_to_string("billing/_cart.html",
                            {"cart": cart}, request=request)
    return JsonResponse({"ok": True,
                         "html": render_to_string("billing/_cart.html", {"cart": cart}, request=request),
                         "count": 0,
                         "total": "0.00",
                         "summary_text": f"({cart.items.count()}) – (${cart.total:.2f})"
                         })


def cart_detail(request):
    """Optional full-page cart view (non-AJAX)."""
    cart = _get_or_create_cart(request)
    get_token(request)  # ensure CSRF cookie
    return render(request, "billing/_cart.html", {"cart": cart})


@login_required
def payment_success(request):
    """
    Handle successful Stripe payment:
    - Create PaymentHistory record
    - Persist all CartItems as Bookings
    - Clear the cart
    - Send confirmation email with receipt
    - Render success page
    """
    try:
        # Retrieve cart safely
        cart_id = request.session.get("cart_id")
        cart = Cart.objects.filter(pk=cart_id, user=request.user).first()

        if not cart or not cart.items.exists():
            messages.error(request, "Your cart is empty or expired.")
            return redirect("billing:checkout")

        # ✅ Derive service address safely
        service_address = (
            getattr(cart, "address_key", None)
            or request.session.get("customer_address")
            or "Unknown"
        ).strip()

        # ✅ Create PaymentHistory record
        payment_record = PaymentHistory.objects.create(
            user=request.user,
            amount=cart.total,
            currency="usd",
            status="Paid",
            service_address=service_address,
            notes="Stripe Checkout Payment",
        )

        # ✅ Create Bookings for all CartItems
        created_bookings = []
        for item in cart.items.all():
            booking = Booking.objects.create(
                user=request.user,
                service_address=service_address,
                service_category=item.service_category,
                date=item.date,
                time_slot=item.time_slot,
                unit_price=item.unit_price,
                total_amount=item.subtotal,
                status="Booked",
            )
            created_bookings.append(booking)

        # ✅ Link bookings ↔ payment
        if created_bookings:
            payment_record.linked_bookings.add(*created_bookings)
            payment_record.save(update_fields=["created_at"])

        # ✅ Clear the cart
        cart.items.all().delete()
        cart.delete()
        request.session.pop("cart_id", None)

        # ✅ Send email receipt (HTML + plain text fallback)
        try:
            send_payment_receipt_email(
                request.user, payment_record, created_bookings, request
            )
            print(f"📧 Sent receipt to {request.user.email}")
        except Exception as e:
            print(f"⚠️ Payment receipt email failed: {e}")

        # ✅ Show confirmation page
        messages.success(
            request,
            f"Payment successful! Your booking for {service_address} has been confirmed.",
        )
        return render(
            request,
            "billing/success.html",
            {"payment_record": payment_record, "bookings": created_bookings},
        )

    except Exception as e:
        print(f"❌ Payment success error: {e}")
        messages.error(request, f"Payment processing error: {e}")
        return redirect("billing:checkout")


@login_required
def payment_history(request):
    """
    Property-centric billing dashboard.
    One card per service address showing all payment activity
    (paid, refunded, adjusted) for the current user.
    """
    from django.db.models import Sum, Q

    # ✅ Update booking statuses for this user (helper)
    _refresh_booking_statuses_for_user(request.user)

    # ✅ All addresses linked to this user's payments
    addresses = (
        PaymentHistory.objects
        .filter(user=request.user)
        .exclude(service_address__isnull=True)
        .values_list("service_address", flat=True)
        .distinct()
    )

    cards = []
    for addr in addresses:
        # Root = initial payment (no parent)
        root = (
            PaymentHistory.objects
            .filter(user=request.user, service_address=addr, parent__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if not root:
            continue

        # Compute section totals safely
        if hasattr(root, "compute_sections"):
            original_total, add_total, cancel_total, net_total = root.compute_sections()
        else:
            # fallback aggregation if compute_sections missing
            all_tx = PaymentHistory.objects.filter(
                user=request.user, service_address=addr)
            original_total = all_tx.filter(parent__isnull=True).aggregate(
                Sum("amount"))["amount__sum"] or 0
            add_total = all_tx.filter(amount__gt=0, parent__isnull=False).aggregate(
                Sum("amount"))["amount__sum"] or 0
            cancel_total = abs(all_tx.filter(amount__lt=0).aggregate(
                Sum("amount"))["amount__sum"] or 0)
            net_total = original_total + add_total - cancel_total

        cards.append({
            "address": addr,
            "root": root,
            "original_total": original_total,
            "add_total": add_total,
            "cancel_total": cancel_total,
            "net_total": net_total,
            "added": root.adjustments.filter(amount__gt=0),
            "cancelled": root.adjustments.filter(amount__lt=0),
        })

    return render(request, "billing/payment_history.html", {
        "cards": cards,
    })
