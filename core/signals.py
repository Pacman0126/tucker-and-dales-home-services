from allauth.account.signals import email_confirmed
from allauth.account.utils import perform_login
from allauth.account.signals import user_signed_up

from django.dispatch import receiver
from django.shortcuts import redirect

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from .models import NewsletterSubscription, first_day_next_month


@receiver(email_confirmed)
def login_after_email_confirmation(request, email_address, **kwargs):
    """Automatically log the user in right after they confirm email."""
    user = email_address.user
    perform_login(request, user, email_verification='optional')
    return redirect('home')


@receiver(user_signed_up)
def send_welcome_email(request, user, **kwargs):
    # (existing welcome email)
    subject = "Welcome to Tucker & Dale’s Home Services!"
    context = {
        "user": user,
        "site_name": "Tucker & Dale’s Home Services",
        "support_email": settings.DEFAULT_FROM_EMAIL,
    }
    html_message = render_to_string(
        "emails/welcome_email.html", context, request=request)
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
        print(f"📧 Sent welcome email to {user.email}")
    except Exception as e:
        print(f"⚠️ Failed to send welcome email: {e}")

    # auto-subscribe and send “you’re subscribed” confirmation
    try:
        next_on = first_day_next_month(timezone.localdate())
        sub, _ = NewsletterSubscription.objects.get_or_create(
            user=user,
            defaults={"next_send_on": next_on},
        )

        ctx = {
            "user": user,
            "first_issue_date": next_on.strftime("%Y-%m-%d"),
            "unsubscribe_url": f"{settings.SITE_BASE_URL}/newsletter/unsubscribe/{sub.token}/",
        }
        html = render_to_string("emails/newsletter_welcome.html", ctx)
        txt = render_to_string("emails/newsletter_welcome.txt", ctx)
        send_mail(
            "You’re subscribed to Tucker & Dale’s Monthly Newsletter",
            txt,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html,
            fail_silently=False,
        )
        print(
            f"📰 Subscribed {user.email}; first issue {next_on} (confirmation sent).")
    except Exception as e:
        print(
            f"⚠️ Newsletter auto-subscribe/notify failed for {user.email}: {e}")
