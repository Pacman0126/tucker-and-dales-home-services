from __future__ import annotations
import logging
from django.contrib import messages
from django.contrib.auth import logout

from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required


from .models import NewsletterSubscription

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


def newsletter_unsubscribe(request, token: str):
    sub = get_object_or_404(NewsletterSubscription, token=token)
    sub.unsubscribed = True
    sub.save(update_fields=["unsubscribed", "updated_at"])
    return render(request, "emails/newsletter_unsubscribed.html", {"email": sub.user.email})


@staff_member_required
def newsletter_send_now(request):
    # quick demo trigger (calls the management command logic inline)
    from django.core.management import call_command
    call_command("send_monthly_newsletter")
    return HttpResponse("Triggered newsletter send.")
