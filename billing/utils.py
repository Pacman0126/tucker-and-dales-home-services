# billing/utils.py
from decimal import Decimal
from django.contrib import messages


def get_service_address(request):
    """Retrieve the currently locked service address for this session."""
    return request.session.get("service_address")


def lock_service_address(request, address: str):
    """Lock a service address into the session for this booking."""
    if not address:
        return
    request.session["service_address"] = address.strip()
    request.session.modified = True
    print(f"🔒 Service address locked for session: {address}")


def _get_or_create_cart(request):
    """
    Retrieve or create a single cart for this session.
    Each cart is locked to a specific service address.
    Lazy import to avoid circular import problems.
    """
    from billing.models import Cart  # lazy import avoids circular deps

    address_key = request.session.get("service_address", "")
    if not request.session.session_key:
        request.session.create()

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(
            user=request.user,
            address_key=address_key,
        )
    else:
        cart, _ = Cart.objects.get_or_create(
            session_key=request.session.session_key,
            address_key=address_key,
        )

    return cart
