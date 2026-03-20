from allauth.account.signals import email_confirmed, user_signed_up
from allauth.account.utils import perform_login

from django.conf import settings
from django.core.mail import send_mail
from django.dispatch import receiver
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from .models import NewsletterSubscription, first_day_next_month


def build_absolute_url(request, path_name, **kwargs):
    """
    Build a stable absolute URL for emails.
    Uses request when available, otherwise falls back to SITE_BASE_URL.
    """
    path = reverse(path_name, kwargs=kwargs)

    if request is not None:
        return request.build_absolute_uri(path)

    base_url = getattr(settings, "SITE_BASE_URL", "").rstrip("/")
    if base_url:
        return f"{base_url}{path}"

    return path


@receiver(email_confirmed)
def login_after_email_confirmation(request, email_address, **kwargs):
    """Automatically log the user in right after they confirm email."""
    user = email_address.user
    perform_login(request, user, email_verification="optional")
    return redirect("core:home")


@receiver(user_signed_up)
def send_welcome_email(request, user, **kwargs):
    subject = "Welcome to Tucker & Dale’s Home Services!"

    dashboard_url = build_absolute_url(request, "core:home")

    context = {
        "user": user,
        "site_name": "Tucker & Dale’s Home Services",
        "support_email": settings.DEFAULT_FROM_EMAIL,
        "site_url": dashboard_url,
    }

    html_message = render_to_string(
        "emails/welcome_email.html",
        context,
        request=request,
    )
    plain_message = strip_tags(html_message)

    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"Sent welcome email to {user.email}")
    except Exception as e:
        print(f"Failed to send welcome email to {user.email}: {e}")

    try:
        next_on = first_day_next_month(timezone.localdate())
        sub, created = NewsletterSubscription.objects.get_or_create(
            user=user,
            defaults={"next_send_on": next_on},
        )

        unsubscribe_url = build_absolute_url(
            request,
            "newsletter:unsubscribe",
            token=sub.token,
        )

        ctx = {
            "user": user,
            "first_issue_date": next_on.strftime("%Y-%m-%d"),
            "unsubscribe_url": unsubscribe_url,
        }

        html = render_to_string(
            "emails/newsletter_welcome.html", ctx, request=request)
        txt = render_to_string(
            "emails/newsletter_welcome.txt", ctx, request=request)

        send_mail(
            "You’re subscribed to Tucker & Dale’s Monthly Newsletter",
            txt,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html,
            fail_silently=False,
        )

        print(
            f"Subscribed {user.email}; first issue {next_on} "
            f"({'created' if created else 'already existed'})"
        )
    except Exception as e:
        print(f"Newsletter auto-subscribe/notify failed for {user.email}: {e}")
