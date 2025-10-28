"""
billing/views.py
Handles checkout, Stripe integration, payment tracking, and admin management.
"""
import datetime
from datetime import datetime as dt
import json
from decimal import Decimal
import stripe

from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from django.utils.timezone import now
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
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
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
    cancel_url = request.build_absolute_uri(reverse("billing:payment_cancel"))

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
def payment_success(request):
    """
    Debug version — adds checkpoint prints to isolate missing subtotal/tax.
    """
    from decimal import Decimal
    from django.utils.timezone import now
    import stripe

    session_id = request.GET.get("session_id")
    if not session_id:
        print("⚠️ Missing session_id → redirecting to checkout")
        messages.warning(request, "Missing Stripe session id.")
        return redirect("billing:checkout")

    print(f"\n🟩 [payment_success] Stripe session_id = {session_id}")

    try:
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["payment_intent", "payment_intent.charges"],
        )
        print("🟢 Retrieved Stripe session successfully.")
    except Exception as e:
        print(f"❌ Stripe session retrieve failed: {e}")
        messages.error(request, f"Could not load Stripe session: {e}")
        return redirect("billing:checkout")

    # --- Stripe raw totals ---
    amount_total = Decimal(session.get("amount_total") or 0) / Decimal("100")
    currency = (session.get("currency") or "usd").lower()
    print(
        f"💵 Stripe totals → amount_total={amount_total}, currency={currency}")

    # --- Metadata ---
    md = session.get("metadata") or {}
    print(f"📦 Metadata received: {md}")

    def to_decimal(val, fallback="0.00"):
        try:
            return Decimal(str(val or fallback))
        except Exception:
            return Decimal(fallback)

    meta_subtotal = to_decimal(md.get("subtotal"))
    meta_tax = to_decimal(md.get("tax"))
    meta_total = to_decimal(md.get("total"))
    service_address = (
        md.get("service_address")
        or request.session.get("service_address")
        or ""
    )

    # --- Fallback checks ---
    if meta_total == 0 and amount_total > 0:
        meta_total = amount_total
    if meta_subtotal == 0 and meta_total > 0:
        meta_subtotal = (meta_total - meta_tax).quantize(Decimal("0.01"))

    print(
        f"🧾 Parsed values → subtotal={meta_subtotal}, tax={meta_tax}, total={meta_total}, service_address='{service_address}'"
    )

    from .models import Cart, PaymentHistory
    cart = Cart.objects.filter(
        user=request.user).order_by("-updated_at").first()

    payment_intent_id = getattr(session.payment_intent, "id", None)
    stripe_payment_id = payment_intent_id or session.id

    # Save / get payment
    ph, created = PaymentHistory.objects.get_or_create(
        user=request.user,
        stripe_payment_id=stripe_payment_id,
        defaults={
            "cart": cart,
            "amount": meta_total or amount_total,
            "currency": currency,
            "service_address": service_address,
            "created_at": now(),
            "raw_data": {
                "stripe_session_id": session.id,
                "payment_intent_id": payment_intent_id,
                "subtotal": f"{meta_subtotal:.2f}",
                "tax": f"{meta_tax:.2f}",
                "total": f"{meta_total:.2f}",
                "service_address": service_address,
                "currency": currency.upper(),
            },
        },
    )

    if created:
        print(f"✅ Created new PaymentHistory id={ph.id}")
    else:
        print(f"♻️ Using existing PaymentHistory id={ph.id}")

    # Clear cart
    if cart and cart.items.exists():
        cleared = cart.items.count()
        cart.items.all().delete()
        print(f"🧹 Cleared {cleared} items from cart.")

    # Reset session
    for key in ("cart_id", "service_address", "address_locked"):
        request.session.pop(key, None)
    request.session.modified = True

    raw = ph.raw_data or {}
    print(f"🧠 raw_data stored in PaymentHistory: {raw}")

    # Values going into context
    context = {
        "transaction_id": ph.stripe_payment_id,
        "subtotal": Decimal(str(raw.get("subtotal", meta_subtotal))),
        "tax": Decimal(str(raw.get("tax", meta_tax))),
        "total": ph.amount,
        "service_address": ph.service_address,
        "currency": ph.currency.upper(),
        "last_payment": ph,
    }

    print("📤 Final context sent to template:", context, "\n")

    return render(request, "billing/success.html", context)


@login_required
def payment_cancel(request):
    """Handles user cancellation from Stripe checkout."""
    messages.info(
        request, "Your payment was cancelled — no charges were made.")
    return redirect("billing:checkout")

# ----------------------------------------------------------------------
# 🧾 Payment History (user)
# ----------------------------------------------------------------------


@login_required
def payment_history(request):
    """Displays all payments for the logged-in user."""
    payments = PaymentHistory.objects.filter(
        user=request.user).select_related("user", "booking").order_by("-created_at")

    return render(request, "billing/payment_history.html", {"payments": payments})


# ----------------------------------------------------------------------
# 🧾 All Payments (admin)
# ----------------------------------------------------------------------
@login_required
def download_receipt_pdf(request, pk):
    """
    Generates a polished, branded PDF receipt for a given PaymentHistory record.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import simpleSplit
    import os

    payment = get_object_or_404(PaymentHistory, pk=pk, user=request.user)

    # ------------------------------------------
    # PDF Response Setup
    # ------------------------------------------
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="receipt_{payment.id}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    y = height - inch

    # ------------------------------------------
    # HEADER with logo or fallback title
    # ------------------------------------------
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.png")
    if os.path.exists(logo_path):
        logo_w, logo_h = 1.3 * inch, 1.3 * inch
        p.drawImage(
            logo_path,
            (width - logo_w) / 2,
            y - logo_h,
            width=logo_w,
            height=logo_h,
            mask="auto",
        )
        y -= logo_h + 0.2 * inch
    else:
        p.setFont("Helvetica-Bold", 18)
        p.drawCentredString(width / 2, y, "Tucker & Dale’s Home Services")
        y -= 0.35 * inch

    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2, y, "Payment Receipt")
    y -= 0.4 * inch

    p.setStrokeColor(colors.lightgrey)
    p.line(inch, y, width - inch, y)
    y -= 0.35 * inch

    # ------------------------------------------
    # BASIC INFO SECTION
    # ------------------------------------------
    info_fields = [
        ("Customer", payment.user.get_full_name() or payment.user.username),
        ("Transaction ID", payment.stripe_payment_id or "N/A"),
        ("Amount Paid", f"${payment.amount:.2f} {payment.currency.upper()}"),
        ("Service Address", payment.service_address or "N/A"),
        ("Date", payment.created_at.strftime("%Y-%m-%d %H:%M:%S")),
    ]

    p.setFont("Helvetica", 12)
    for label, value in info_fields:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(inch, y, f"{label}:")
        p.setFont("Helvetica", 12)
        # Wrap long values automatically
        wrapped = simpleSplit(str(value), "Helvetica", 12, width - 2.8 * inch)
        for line in wrapped:
            p.drawString(inch + 1.8 * inch, y, line)
            y -= 0.25 * inch
        y -= 0.05 * inch

    y -= 0.2 * inch
    p.line(inch, y, width - inch, y)
    y -= 0.3 * inch

    # ------------------------------------------
    # PAYMENT DETAILS SECTION
    # ------------------------------------------
    p.setFont("Helvetica-Bold", 13)
    p.drawString(inch, y, "Payment Details:")
    y -= 0.3 * inch

    raw = payment.raw_data if isinstance(payment.raw_data, dict) else {}
    subtotal = raw.get("subtotal", "N/A")
    tax = raw.get("tax", "N/A")
    total = raw.get("total", f"{payment.amount:.2f}")
    session_id = raw.get("stripe_session_id", "N/A")
    payment_intent = raw.get("payment_intent_id", "N/A")

    details = [
        ("Subtotal", f"${subtotal}"),
        ("Tax", f"${tax}"),
        ("Total", f"${total}"),
        ("Stripe Session ID", session_id),
        ("Payment Intent ID", payment_intent),
    ]

    p.setFont("Helvetica", 11)
    for label, value in details:
        p.setFont("Helvetica-Bold", 11)
        p.drawString(inch, y, f"{label}:")
        p.setFont("Helvetica", 11)
        wrapped = simpleSplit(str(value), "Helvetica", 11, width - 2.8 * inch)
        for line in wrapped:
            p.drawString(inch + 1.8 * inch, y, line)
            y -= 0.22 * inch
        y -= 0.05 * inch

    # ------------------------------------------
    # FOOTER
    # ------------------------------------------
    y -= 0.3 * inch
    p.setStrokeColor(colors.lightgrey)
    p.line(inch, y, width - inch, y)
    y -= 0.3 * inch

    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.grey)
    p.drawCentredString(width / 2, y, "Thank you for your payment!")
    p.drawCentredString(width / 2, y - 0.2 * inch,
                        "Tucker & Dale’s Home Services © 2025")
    p.setFillColor(colors.black)

    p.showPage()
    p.save()
    return response


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
@require_POST
def cancel_selected_services(request):
    """
    Cancels selected paid services.
    - 50% refund if within 72h window
    - Full refund if ≥72h before scheduled time
    - Records refund in PaymentHistory + links back to Booking
    - Updates booking.status and total_amount accordingly
    """
    from decimal import Decimal
    import stripe
    from django.utils.timezone import now
    from django.db import transaction
    from billing.models import PaymentHistory
    from scheduling.models import Booking

    payment_ids = request.POST.getlist("selected_payments")
    if not payment_ids:
        return JsonResponse({"ok": False, "error": "No services selected."})

    payments = PaymentHistory.objects.filter(
        id__in=payment_ids, user=request.user
    ).prefetch_related("bookings")

    if not payments.exists():
        return JsonResponse({"ok": False, "error": "No valid payment records found."})

    results = []

    for pay in payments:
        booking = pay.bookings.first()  # use new M2M relation
        hours_until = booking.hours_until if booking else 9999
        penalty = hours_until < 72
        refund_amt = pay.amount * \
            (Decimal("0.5") if penalty else Decimal("1.0"))
        note = "50% penalty (within 72h)" if penalty else "Full refund"

        refund_obj = None
        try:
            intent_id = pay.raw_data.get("payment_intent_id")
            if intent_id:
                # Stripe sandbox refund (optional)
                refund_obj = stripe.Refund.create(
                    payment_intent=intent_id,
                    amount=int(refund_amt * 100)
                )
        except stripe.error.StripeError as e:
            note += f" (Stripe error: {e})"

        # --- transactional update ---
        with transaction.atomic():
            refund_entry = PaymentHistory.objects.create(
                user=request.user,
                amount=-refund_amt,
                currency=pay.currency,
                service_address=pay.service_address,
                created_at=now(),
                status="Refunded",
                payment_type="REFUND",
                notes=f"Cancelled booking — {note}",
                raw_data={
                    "original_payment_id": pay.id,
                    "stripe_refund_id": getattr(refund_obj, "id", None),
                    "penalty_applied": penalty,
                },
            )

            # link refund to same booking
            if booking:
                booking.payments.add(refund_entry)
                booking.status = "Cancelled"
                booking.total_amount = booking.total_amount - refund_amt
                booking.save(update_fields=[
                             "status", "total_amount", "updated_at"])

            # mark old record
            pay.status = "Cancelled"
            pay.save(update_fields=["status", "updated_at"])

        results.append({
            "payment_id": pay.id,
            "refund_amount": float(refund_amt),
            "penalty": penalty,
            "refund_id": getattr(refund_obj, "id", None)
        })

    return JsonResponse({
        "ok": True,
        "summary": f"{len(results)} service(s) cancelled successfully.",
        "results": results,
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
    return render(request, "scheduling/cart_detail.html", {"cart": cart})
