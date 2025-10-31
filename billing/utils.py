__all__ = ["_get_or_create_cart",
           "get_service_address", "lock_service_address"]
from decimal import Decimal
from typing import Optional
from datetime import datetime, timedelta
from django.contrib import messages
from django.utils import timezone
from django.utils.timezone import now
from billing.models import Cart, CartItem


# def merge_session_cart(session_key: str, user):
#     """
#     Attach any existing anonymous cart (by session_key)
#     to the now-authenticated user.
#     """
#     if not session_key:
#         return

#     try:
#         session_cart = Cart.objects.filter(session_key=session_key).first()
#         if session_cart:
#             session_cart.user = user
#             session_cart.session_key = None
#             session_cart.save(update_fields=["user", "session_key"])
#             print(f"🛒 Merged cart {session_cart.id} → {user.username}")
#     except Exception as e:
#         print(f"⚠️ merge_session_cart() failed: {e}")


def _clear_cart_for_session(request):
    """
    Clears all cart items for this session (used when address changes).
    """
    if request.user.is_authenticated:
        Cart.objects.filter(user=request.user).delete()
    else:
        if request.session.session_key:
            Cart.objects.filter(
                session_key=request.session.session_key).delete()
    request.session.modified = True
    print("🧹 Cleared cart due to address change.")


# ============================================================
# 🏠 SERVICE ADDRESS SESSION MANAGEMENT
# ============================================================
def get_service_address(request) -> str:
    """
    Return the currently locked service address for this session.
    (Never mutate here.)
    """
    return normalize_address(request.session.get("service_address"))


def lock_service_address(request, address: str) -> None:
    """
    Lock the service address for this booking session and flip the lock flag.
    """
    addr = normalize_address(address)
    if not addr:
        return
    request.session["service_address"] = addr
    request.session["address_locked"] = True
    request.session.modified = True


def unlock_service_address(request) -> None:
    """
    Clear the service address and lock flag.
    (Used by 'Book for New Address'.)
    """
    request.session.pop("service_address", None)
    request.session.pop("address_locked", None)
    request.session.pop("cart_id", None)
    request.session.modified = Tru


def normalize_address(address: Optional[str]) -> str:
    return (address or "").strip()

# ============================================================
# 🛒 CART UTILITIES
# ============================================================


def _get_or_create_cart(request) -> Cart:
    """
    Legacy helper (kept because several views import it).
    Prefer `get_active_cart_for_request`, but this remains compatible.

    Strategy:
    - If session carries a cart_id -> return that cart (and ensure ownership).
    - Else, if user is authenticated -> return latest cart with the session's
      service address_key (if set) or the most recent cart; create if none.
    - Else (anonymous) -> return/create a session cart keyed by session_key + address_key.
    """
    return get_active_cart_for_request(request, create_if_missing=True)


# ============================================================
# 🔧 Safe external getter (used by login / merge workflows)
# ============================================================
def get_or_create_cart(request_or_user):
    """
    Public wrapper that can safely be imported from other apps.
    Works with either a request or a user instance.
    """
    from billing.models import Cart

    if hasattr(request_or_user, "user"):  # got a request
        request = request_or_user
        user = getattr(request, "user", None)
        session_key = request.session.session_key
    else:  # got a user
        request = None
        user = request_or_user
        session_key = None

    if user and user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=user)
    else:
        cart, _ = Cart.objects.get_or_create(session_key=session_key)

    return cart


def get_active_cart_for_request(request, *, create_if_missing: bool = True) -> Optional[Cart]:
    """
    Single source of truth for selecting the active cart.
    1) Honor session["cart_id"] if present.
    2) Otherwise, use (user, address_key) if authenticated.
    3) Otherwise, use (session_key, address_key) for guests.

    This never silently switches address_key. The address is the session’s boss.
    """
    address_key = normalize_address(request.session.get("service_address"))
    cart_id = request.session.get("cart_id")

    # 1) If we have a pinned cart_id, use it.
    if cart_id:
        try:
            cart = Cart.objects.select_related().get(pk=cart_id)
            # Guard: if this cart belongs to another user, take ownership on login
            if request.user.is_authenticated and cart.user_id != request.user.id:
                cart.user = request.user
                cart.session_key = request.session.session_key
                cart.save(update_fields=["user", "session_key", "updated_at"])
            return cart
        except Cart.DoesNotExist:
            # stale id, drop it and continue
            request.session.pop("cart_id", None)
            request.session.modified = True

    # Ensure a session_key exists for anonymous carts
    if not request.session.session_key:
        request.session.create()

    # 2) Authenticated user → prefer a cart with this address_key
    if request.user.is_authenticated:
        qs = Cart.objects.filter(user=request.user)
        if address_key:
            cart = qs.filter(address_key=address_key).order_by(
                "-updated_at").first()
            if cart:
                request.session["cart_id"] = cart.pk
                request.session.modified = True
                return cart
        cart = qs.order_by("-updated_at").first()
        if cart:
            # If the cart has no address yet and the session does, apply it.
            if address_key and normalize_address(cart.address_key) != address_key:
                cart.address_key = address_key
                cart.save(update_fields=["address_key", "updated_at"])
            request.session["cart_id"] = cart.pk
            request.session.modified = True
            return cart
        if not create_if_missing:
            return None
        # Create a new user cart pinned to session address (if any)
        cart = Cart.objects.create(
            user=request.user, address_key=address_key or "")
        request.session["cart_id"] = cart.pk
        request.session.modified = True
        return cart

    # 3) Anonymous user → use session cart
    if not create_if_missing:
        return None
    cart, _ = Cart.objects.get_or_create(
        session_key=request.session.session_key,
        address_key=address_key or "",
        defaults={"created_at": now()},
    )
    request.session["cart_id"] = cart.pk
    request.session.modified = True
    return cart


def merge_session_cart(old_session_key: str, user) -> Optional[Cart]:
    """
    Merge all carts that were created for the old_session_key into the user’s active cart.
    We prefer to keep the address_key from the current session (if present).
    """
    if not old_session_key or not user:
        return None

    # Collect all session carts
    session_carts = Cart.objects.filter(
        session_key=old_session_key).order_by("updated_at")
    if not session_carts.exists():
        return None

    # Choose / prepare the destination cart for this user
    # If the session already has a service_address, we’ll pin to that
    target_address = normalize_address(user._request.session.get(
        "service_address") if hasattr(user, "_request") else None)
    if target_address:
        main = Cart.objects.filter(
            user=user, address_key=target_address).order_by("-updated_at").first()
        if not main:
            main = Cart.objects.create(user=user, address_key=target_address)
    else:
        main = Cart.objects.filter(user=user).order_by(
            "-updated_at").first() or Cart.objects.create(user=user)

    moved = 0
    for sc in session_carts:
        for item in sc.items.all():
            item.cart = main
            item.save(update_fields=["cart"])
            moved += 1
        sc.delete()

    # Pin merged cart to session
    # NOTE: we cannot access request here directly; caller should set cart_id.
    return main


def get_refund_policy(booking_datetime):
    """
    Determine refund eligibility and percentage based on time before service.
    Returns tuple (status, refund_percent).
    """
    if not booking_datetime:
        return ("Locked", 0)

    now = timezone.now()
    # assume booking_datetime is a datetime or date
    if isinstance(booking_datetime, datetime):
        booking_dt = booking_datetime
    else:
        booking_dt = datetime.combine(
            booking_datetime, datetime.min.time(), tzinfo=timezone.get_current_timezone())

    delta = booking_dt - now
    hours_until = delta.total_seconds() / 3600

    if hours_until >= 72:
        return ("Cancellable", 100)
    elif 0 < hours_until < 72:
        return ("Late Cancel", 50)
    else:
        return ("Locked", 0)
