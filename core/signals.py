# core/signals.py
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


@receiver(user_signed_up)
@receiver(user_signed_up)
def send_welcome_email(request, user, **kwargs):
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
