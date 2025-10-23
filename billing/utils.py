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
    """Lock a service address for the session once the first search runs."""
    if address:
        normalized = address.strip()
        request.session["service_address"] = normalized
        request.session["address_locked"] = True
        request.session.modified = True
        print(f"🔒 Locked service address: {normalized}")


def unlock_service_address(request):
    """Unlock and clear address + related cart session keys."""
    for key in ("service_address", "address_locked", "cart_id"):
        request.session.pop(key, None)
    request.session.modified = True
    print("🔓 Service address unlocked for new booking")


def normalize_address(address: str) -> str:
    """Normalize address for consistent key comparison."""
    return address.strip().lower() if address else ""

# ============================================================
# 🛒 CART UTILITIES
# ============================================================


def _get_or_create_cart(request):
    """Retrieve or create a cart tied to either user or session."""
    address_key = request.session.get("service_address", "")
    if not request.session.session_key:
        request.session.create()

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(
            user=request.user,
            address_key=address_key or "",
        )
    else:
        cart, _ = Cart.objects.get_or_create(
            session_key=request.session.session_key,
            address_key=address_key or "",
        )

    request.session["cart_id"] = str(cart.id)
    request.session.modified = True
    return cart


def merge_session_cart(old_session_key, user):
    """Merge guest cart into user cart after login."""
    try:
        guest_cart = Cart.objects.filter(session_key=old_session_key).first()
        if not guest_cart:
            return
        user_cart, _ = Cart.objects.get_or_create(user=user)
        for item in guest_cart.items.all():
            item.cart = user_cart
            item.save()
        guest_cart.delete()
    except Exception as e:
        print(f"⚠️ Cart merge failed: {e}")


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
