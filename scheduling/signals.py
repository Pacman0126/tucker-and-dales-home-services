from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from .models import Cart


@receiver(user_logged_out)
def clear_cart_on_logout(sender, request, user, **kwargs):
    """
    When a user logs out, clear their active cart to avoid leftover items.
    """
    try:
        if user and hasattr(user, "carts"):
            Cart.objects.filter(user=user).delete()
        # also remove any session cart
        if request and request.session.session_key:
            Cart.objects.filter(
                session_key=request.session.session_key).delete()
    except Exception as e:
        print(f"⚠️ Failed to clear cart on logout: {e}")
