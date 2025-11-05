# core/management/commands/send_monthly_newsletter.py
from __future__ import annotations
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import date, timedelta
from core.models import NewsletterSubscription, first_day_next_month


class Command(BaseCommand):
    help = "Send monthly newsletter to subscribed users whose next_send_on is today (1st of the month)."

    def handle(self, *args, **options):
        today = timezone.localdate()
        qs = NewsletterSubscription.objects.select_related("user").filter(
            unsubscribed=False,
            next_send_on__lte=today,
        )
        sent = 0

        for sub in qs:
            user = sub.user
            # Render email
            ctx = {
                "user": user,
                "send_date": today.strftime("%Y-%m-%d"),
                "unsubscribe_url": f"{settings.SITE_BASE_URL}/newsletter/unsubscribe/{sub.token}/",
            }
            subject = "🗞️ Your Tucker & Dale’s Monthly Newsletter"
            html_body = render_to_string("emails/newsletter_monthly.html", ctx)
            text_body = render_to_string("emails/newsletter_monthly.txt", ctx)

            try:
                send_mail(
                    subject,
                    text_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_body,
                    fail_silently=False,
                )
                sent += 1
                # Move to next month (always 1st)
                sub.next_send_on = first_day_next_month(today)
                sub.save(update_fields=["next_send_on", "updated_at"])
                self.stdout.write(self.style.SUCCESS(
                    f"Sent newsletter to {user.email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Failed to send to {user.email}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Sent={sent}"))
