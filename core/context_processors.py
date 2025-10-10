def cart_summary(request):
    cart = request.session.get("cart", {})
    count = sum(item.get("qty", 1) for item in cart.values())
    total = sum(item.get("price", 0) * item.get("qty", 1)
                for item in cart.values())
    return {"CART_COUNT": count, "CART_TOTAL": total}
