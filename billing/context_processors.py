from decimal import Decimal
from billing.models import Cart


def cart_summary(request):
    cart = request.session.get("cart", {})
    count = sum(item.get("qty", 1) for item in cart.values())
    total = sum(item.get("price", 0) * item.get("qty", 1)
                for item in cart.values())
    return {"CART_COUNT": count, "CART_TOTAL": total}


def cart_context(request):
    """
    Injects cart summary into all templates.
    This allows the navbar to display item count and total dynamically.
    """
    cart_data = {"item_count": 0, "subtotal": Decimal("0.00")}

    try:
        # You can adapt this to how your Cart model/session is structured
        cart = Cart.objects.get_for_request(request)
        cart_data["item_count"] = cart.items.count()
        cart_data["subtotal"] = cart.subtotal
    except Exception:
        pass  # Ignore errors if cart/session not initialized

    return {"cart_summary": cart_data}
