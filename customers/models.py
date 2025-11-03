from django.db import models
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# Create your models here.


class CustomerProfile(models.Model):
    """
    Single, canonical profile for each auth user.
    Holds contact info + billing address used in checkout_summary, etc.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )

    # ── Contact / identity (optional) ─────────────────────────────────────────────
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=120, blank=True)
    preferred_contact = models.CharField(
        max_length=16,
        choices=[("email", "Email"), ("phone", "Phone")],
        default="email",
    )
    timezone = models.CharField(max_length=64, blank=True)

    # ── Billing address (THIS IS WHAT checkout_summary RELIES ON) ────────────────
    billing_street_address = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_zipcode = models.CharField(max_length=20, blank=True)
    # region is used in your view to store "billing_country"
    region = models.CharField(
        # ISO-2 country code like "US", "DE" (adjust if you prefer)
        max_length=2,
        blank=True,
        help_text="Country/region code (e.g., US, DE).",
    )

    # ── (Optional) last-known service address snapshot for UX shortcuts ──────────
    service_street_address = models.CharField(max_length=255, blank=True)
    service_city = models.CharField(max_length=100, blank=True)
    service_state = models.CharField(max_length=100, blank=True)
    service_zipcode = models.CharField(max_length=20, blank=True)
    service_region = models.CharField(max_length=2, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]
        verbose_name = "Customer Profile"
        verbose_name_plural = "Customer Profiles"

    def __str__(self) -> str:
        return f"CustomerProfile<{self.user.username}>"

    # ── Helpers the views/templates call ─────────────────────────────────────────
    def has_valid_billing_address(self) -> bool:
        return all(
            [
                self.billing_street_address.strip(),
                self.billing_city.strip(),
                self.billing_state.strip(),
                self.billing_zipcode.strip(),
                self.region.strip(),
            ]
        )

    @property
    def full_billing_address(self) -> str:
        """
        The view expects a single string like:
        '123 Main St, Dallas, TX 75001, US'
        """
        parts = [
            (self.billing_street_address or "").strip(),
            (self.billing_city or "").strip(),
            (self.billing_state or "").strip(),
            (self.billing_zipcode or "").strip(),
        ]
        main = ", ".join([p for p in parts if p])
        tail = (self.region or "").strip()
        return f"{main}, {tail}" if tail else main

    def has_valid_service_address(self) -> bool:
        return all(
            [
                self.service_street_address.strip(),
                self.service_city.strip(),
                self.service_state.strip(),
                self.service_zipcode.strip(),
                self.service_region.strip(),
            ]
        )

    @property
    def full_service_address(self) -> str:
        parts = [
            (self.service_street_address or "").strip(),
            (self.service_city or "").strip(),
            (self.service_state or "").strip(),
            (self.service_zipcode or "").strip(),
        ]
        main = ", ".join([p for p in parts if p])
        tail = (self.service_region or "").strip()
        return f"{main}, {tail}" if tail else main
