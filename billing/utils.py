__all__ = ["_get_or_create_cart",
           "get_service_address", "lock_service_address"]
from decimal import Decimal
from typing import Optional
from django.contrib import messages
from billing.models import Cart


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

def get_service_address(request):
    """Retrieve the locked service address for this session."""
    return request.session.get("service_address")


def lock_service_address(request, address: str):
    if not address:
        return
    request.session["service_address"] = address.strip()
    request.session.modified = True
    print(f"🔒 Service address locked for session: {address}")


def unlock_service_address(request):
    """Unlock and clear address + related cart session keys."""
    for key in ("service_address", "address_locked", "cart_id"):
        request.session.pop(key, None)
    request.session.modified = True
    print("🔓 Service address unlocked for new booking")


def normalize_address(addr: str | None) -> str:
    return (addr or "").strip().lower()

# ============================================================
# 🛒 CART UTILITIES
# ============================================================


def _get_or_create_cart(request):
    """
    One cart per (user OR session_key) + address_key.
    NEVER treat a blank address as a “new address”.
    """
    address_key = normalize_address(request.session.get("service_address"))
    if not request.session.session_key:
        request.session.create()

    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            address_key=address_key or None,   # store None if blank
        )
    else:
        cart, created = Cart.objects.get_or_create(
            session_key=request.session.session_key,
            address_key=address_key or None,   # store None if blank
        )

    # Remember active cart id for navbar badge, etc.
    request.session["cart_id"] = cart.id
    request.session.modified = True
    return cart


def merge_session_cart(old_session_key: str, user):
    """
    Merge an anonymous session cart (pre-login) into the logged-in user's active cart.
    Keeps the newest address_key if both exist.
    """
    from billing.models import Cart, CartItem

    if not old_session_key or not user:
        return None

    try:
        session_carts = Cart.objects.filter(session_key=old_session_key)
        user_carts = Cart.objects.filter(user=user)
        if not session_carts.exists():
            return None

        # Get or create main cart for user
        main_cart = user_carts.order_by(
            "-updated_at").first() or Cart.objects.create(user=user)

        for sc in session_carts:
            for item in sc.items.all():
                item.cart = main_cart
                item.save()
            sc.delete()

        return main_cart
    except Exception as e:
        print(f"⚠️ merge_session_cart error: {e}")
        return None


# def _get_or_create_cart(request):
#     """
#     Retrieve or create a persistent cart for the current user/session.
#     Each session has at most one active cart tied to its locked service address.
#     """
#     # --- Ensure session exists ---
#     if not request.session.session_key:
#         request.session.create()

#     session_key = request.session.session_key
#     address_key = (request.session.get("service_address") or "").strip()

#     # --- Pick correct identifier (user vs session) ---
#     filters = {"address_key": address_key}
#     if request.user.is_authenticated:
#         filters["user"] = request.user
#     else:
#         filters["session_key"] = session_key

#     # --- Try existing cart first ---
#     cart = Cart.objects.filter(**filters).order_by("-updated_at").first()

#     # --- If not found, create new ---
#     if not cart:
#         cart = Cart.objects.create(**filters)

#     # --- Persist cart id in session for quick access ---
#     request.session["cart_id"] = cart.id
#     request.session.modified = True
#     return cart
