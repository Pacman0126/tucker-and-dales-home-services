from decimal import Decimal
from billing.models import Cart
from billing.utils import _get_or_create_cart


def cart_summary(request):
    """
    Provides cart summary (count and total) to all templates,
    ensuring navbar badge and totals persist across pages.
    """
    try:
        cart = _get_or_create_cart(request)
        return {
            "cart_item_count": cart.item_count,
            "cart_total": f"{cart.total:.2f}",
        }
    except Exception:
        return {"cart_item_count": 0, "cart_total": "0.00"}


def cart_context(request):
    """
    Injects cart summary into all templates.
    This allows the navbar to display item count and total dynamically.
    """
    cart_data = {"item_count": 0, "subtotal": Decimal("0.00")}

    try:

        cart = Cart.objects.get_for_request(request)
        cart_data["item_count"] = cart.items.count()
        cart_data["subtotal"] = cart.subtotal
    except Exception:
        pass  # Ignore errors if cart/session not initialized

    return {"cart_summary": cart_data}


def cart_badge(request):
    """
    Global cart summary for navbar badge / booking summary.
    Keeps badge consistent across all pages and search modes.
    """
    cart = None

    if request.user.is_authenticated:
        cart = (
            Cart.objects.filter(user=request.user)
            .prefetch_related("items")
            .order_by("-updated_at")
            .first()
        )
    else:
        session_key = request.session.session_key
        if session_key:
            cart = (
                Cart.objects.filter(session_key=session_key)
                .prefetch_related("items")
                .order_by("-updated_at")
                .first()
            )

    if not cart:
        return {
            "cart_item_count": 0,
            "cart_total": Decimal("0.00"),
        }

    return {
        "cart_item_count": cart.items.count(),
        "cart_total": cart.total,
    }
