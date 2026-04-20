# core/management/commands/send_monthly_newsletter.py
from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from core.models import NewsletterSubscription, first_day_next_month


class Command(BaseCommand):
    help = (
        "Send monthly newsletter to subscribed users. "
        "Default mode sends only to users due today. "
        "Use --force to send immediately to all subscribed users."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Send immediately to all subscribed users, "
                "ignoring next_send_on."
            ),
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        force = options.get("force", False)

        qs = NewsletterSubscription.objects.select_related("user").filter(
            unsubscribed=False,
        )

        if not force:
            qs = qs.filter(next_send_on__lte=today)

        sent = 0
        failed = 0

        base_url = getattr(settings, "SITE_BASE_URL", "").rstrip("/")

        for sub in qs:
            user = sub.user

            if not user.email:
                failed += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping user {user.pk} - no email address."
                    )
                )
                continue

            ctx = {
                "user": user,
                "send_date": today.strftime("%Y-%m-%d"),
                "unsubscribe_url": (
                    f"{base_url}/newsletter/unsubscribe/{sub.token}/"
                    if base_url
                    else f"/newsletter/unsubscribe/{sub.token}/"
                ),
            }

            subject = "🗞️ Your Tucker & Dale’s Monthly Newsletter"
            html_body = render_to_string(
                "emails/newsletter_monthly.html",
                ctx,
            )
            text_body = render_to_string(
                "emails/newsletter_monthly.txt",
                ctx,
            )

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

                if not force:
                    sub.next_send_on = first_day_next_month(today)
                    sub.save(update_fields=["next_send_on", "updated_at"])

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Sent newsletter to {user.email}"
                    )
                )
            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to send to {user.email}: {e}"
                    )
                )

        mode = "FORCE" if force else "SCHEDULED"
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Mode={mode} Sent={sent} Failed={failed}"
            )
        )
