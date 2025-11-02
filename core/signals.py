from allauth.account.signals import email_confirmed
from allauth.account.utils import perform_login
from django.dispatch import receiver
from django.shortcuts import redirect
from allauth.account.signals import user_signed_up
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


@receiver(user_signed_up)
def send_welcome_email(request, user, **kwargs):
    subject = "Welcome to Tucker & Dale’s Home Services!"

    # ✅ Safely build absolute site URL
    if request:
        site_url = request.build_absolute_uri(
            "/")  # e.g. http://127.0.0.1:8000/
    else:
        site_url = "https://tucker-and-dales-home-services.herokuapp.com/"

    context = {
        "user": user,
        "site_name": "Tucker & Dale’s Home Services",
        "site_url": site_url,  # 🔥 pass to template
        "support_email": settings.DEFAULT_FROM_EMAIL,
    }

    html_message = render_to_string("emails/welcome_email.html", context)
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


@receiver(email_confirmed)
def login_after_email_confirmation(request, email_address, **kwargs):
    """Automatically log the user in right after they confirm email."""
    user = email_address.user
    perform_login(request, user, email_verification='optional')
    return redirect('home')
