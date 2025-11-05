from __future__ import annotations
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from datetime import date
import secrets

User = get_user_model()


class Address(models.Model):
    # Optional owner so a user can manage multiple service addresses
    owner = models.ForeignKey(User, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="addresses")
    # “Home”, “Rental A”, etc.
    label = models.CharField(max_length=100, blank=True)
    line1 = models.CharField(max_length=128)
    line2 = models.CharField(max_length=128, blank=True)
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=32, blank=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=2, default="US")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "line1", "line2", "city",
                        "state", "postal_code", "country"],
                name="uq_owner_address_full"
            )
        ]

    def __str__(self):
        base = f"{self.line1}, {self.city}"
        return f"{self.label} • {base}" if self.label else base


User = settings.AUTH_USER_MODEL


def first_day_next_month(d: date | None = None) -> date:
    d = d or timezone.localdate()
    y, m = d.year, d.month
    if m == 12:
        return date(y + 1, 1, 1)
    return date(y, m + 1, 1)


class NewsletterSubscription(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="newsletter_sub"
    )
    # first send date (always set to the 1st of the *next* month at signup)
    next_send_on = models.DateField(default=first_day_next_month)
    unsubscribed = models.BooleanField(default=False)
    token = models.CharField(max_length=32, unique=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["next_send_on"]),
            models.Index(fields=["unsubscribed"]),
        ]

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_hex(16)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"NewsletterSubscription<{self.user}> unsub={self.unsubscribed}, next={self.next_send_on}"
