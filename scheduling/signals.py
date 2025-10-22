from django.contrib.auth.signals import user_logged_out, user_logged_in
from django.dispatch import receiver
from billing.models import Cart, CartItem


@receiver(user_logged_out)
def clear_cart_on_logout(sender, request, user, **kwargs):
    """
    Automatically clears the authenticated user's cart when they log out.
    """
    if not user or not user.is_authenticated:
        return
    try:
        cart = Cart.objects.filter(user=user).order_by("-updated_at").first()
        if cart:
            cart.items.all().delete()
    except Exception as e:
        print(f"⚠️ Cart cleanup on logout failed: {e}")


@receiver(user_logged_in)
def attach_session_cart_to_user(sender, request, user, **kwargs):
    """
    When a user logs in, merge any session-based cart into their user cart.
    """
    try:
        session_key = getattr(request, "session",
                              None) and request.session.session_key
        if not session_key:
            return

        # The cart you built while anonymous
        session_cart = Cart.objects.filter(
            session_key=session_key).order_by("-updated_at").first()
        if not session_cart or not session_cart.items.exists():
            return

        # The user's persistent cart
        user_cart, _ = Cart.objects.get_or_create(user=user)

        # Move/merge items (respecting unique_together on CartItem)
        for it in list(session_cart.items.all()):
            CartItem.objects.update_or_create(
                cart=user_cart,
                service_category=it.service_category,
                time_slot=it.time_slot,
                date=it.date,
                employee=it.employee,
                defaults={"unit_price": it.unit_price,
                          "quantity": it.quantity},
            )

        # Remove the old session cart
        session_cart.delete()

    except Exception as e:
        print(f"⚠️ Failed to merge session cart on login: {e}")
