from django.contrib import messages
from django.utils import timezone


def get_locked_address(request):
    """
    Retrieve the locked service address from session (if any).
    Returns: (address_string, is_locked_boolean)
    """
    locked_address = request.session.get("service_address", "")
    return locked_address.strip(), bool(locked_address)


def lock_service_address(request, address):
    """
    Lock a service address for the current booking session.
    Ensures consistency across multiple searches and cart operations.
    """
    if not address:
        return

    request.session["service_address"] = address.strip()
    request.session["address_locked"] = True
    request.session.modified = True
    print(f"🔒 Session locked to service address: {address}")


def clear_locked_address(request, with_message=True):
    """
    Clears the locked address (used when clicking 'Book for New Address').
    Also clears related cart and session flags.
    """
    from billing.models import Cart

    old_address = request.session.pop("service_address", None)
    request.session.pop("address_locked", None)

    # Optionally clear cart if tied to previous address
    if old_address:
        try:
            Cart.objects.filter(
                session_key=request.session.session_key).delete()
            print(f"🧹 Cleared cart for previous address: {old_address}")
        except Exception as e:
            print(f"⚠️ Failed to clear old cart: {e}")

    request.session.modified = True

    if with_message:
        messages.info(
            request,
            "Your previous cart was cleared — you can now book under a new address."
        )
