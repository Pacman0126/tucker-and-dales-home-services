from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import NewsletterSubscription
import logging

logger = logging.getLogger(__name__)


def home(request):
    logger.info("Home page accessed")
    return render(request, "core/home.html", {"navbar_mode": "home"})


def custom_404(request, exception):
    return render(request, "errors/404.html", status=404)


def custom_500(request):
    return render(request, "errors/500.html", status=500)


def custom_logout(request):
    """
    Legacy fallback only.
    Prefer allauth's /accounts/logout/ route in templates.
    """
    logout(request)
    messages.info(
        request, "You've been logged out — your cart has been cleared.")
    return redirect("core:home")


def newsletter_unsubscribe(request, token: str):
    sub = get_object_or_404(NewsletterSubscription, token=token)
    sub.unsubscribed = True
    sub.save(update_fields=["unsubscribed", "updated_at"])
    return render(request, "emails/newsletter_unsubscribed.html",
                  {"email": sub.user.email})


@staff_member_required
def newsletter_send_now(request):
    from django.core.management import call_command
    call_command("send_monthly_newsletter")
    return HttpResponse("Triggered newsletter send.")


def test_500(request):
    raise Exception("Deliberate test 500")


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Allow: /",
        f"Sitemap: {settings.SITE_BASE_URL}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
