# core/views.py
import logging
from io import StringIO

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import logout

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from customers.models import CustomerProfile

from .models import NewsletterSubscription

logger = logging.getLogger(__name__)


def home(request):
    logger.info("Home page accessed")

    if request.user.is_authenticated and not request.user.is_staff:
        placeholder_phone = "000-000-0000"
        profile = CustomerProfile.objects.filter(user=request.user).first()

        if not profile:
            messages.warning(
                request,
                "Please complete your profile before continuing."
            )
            return redirect("customers:complete_profile")

        if not profile.phone or profile.phone.strip() == placeholder_phone:
            messages.warning(
                request,
                "Please complete your profile, including a valid phone "
                "number, before continuing."
            )
            return redirect("customers:complete_profile")

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
        request, "You've been logged out — your cart has been cleared."
    )
    return redirect("core:home")


def newsletter_unsubscribe(request, token: str):
    sub = get_object_or_404(NewsletterSubscription, token=token)
    sub.unsubscribed = True
    sub.save(update_fields=["unsubscribed", "updated_at"])
    return render(
        request,
        "emails/newsletter_unsubscribed.html",
        {"email": sub.user.email},
    )


@staff_member_required
def newsletter_send_now(request):
    import re
    from io import StringIO
    from django.core.management import call_command

    out = StringIO()

    try:
        call_command(
            "send_monthly_newsletter",
            force=True,
            stdout=out,
        )

        output = out.getvalue()

        # Remove ANSI color codes from management command output
        clean_output = re.sub(r"\x1b\[[0-9;]*m", "", output)

        sent = 0
        failed = 0

        for line in clean_output.splitlines():
            if "Done." in line:
                match_sent = re.search(r"Sent=(\d+)", line)
                match_failed = re.search(r"Failed=(\d+)", line)

                if match_sent:
                    sent = int(match_sent.group(1))
                if match_failed:
                    failed = int(match_failed.group(1))

        return HttpResponse(
            (
                f"Newsletter forced successfully. "
                f"Sent: {sent}, Failed: {failed}."
            )
        )

    except Exception as e:
        return HttpResponse(
            f"Newsletter send failed: {e}",
            status=500,
        )


def test_500(request):
    raise Exception("Deliberate test 500")


def robots_txt(request):
    base_url = getattr(settings, "SITE_BASE_URL", "").rstrip("/")
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Allow: /",
        f"Sitemap: {base_url}/sitemap.xml" if base_url else "Sitemap: /sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
