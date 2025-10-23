import logging
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import render, redirect

# Use __name__ so logs show "core.views"
logger = logging.getLogger(__name__)


def home(request):
    logger.info("Home page accessed")
    return render(request, "core/home.html", {"navbar_mode": "home"})


def custom_logout(request):
    """
    Logs out the user and shows a friendly message on redirect.
    The scheduling.signals.clear_cart_on_logout will handle cart cleanup.
    """
    logout(request)
    messages.info(
        request, "You've been logged out — your cart has been cleared.")
    return redirect("home")
