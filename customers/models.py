from django.db import models
import uuid
from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class RegisteredCustomer(models.Model):
    """
    Represents a registered customer linked to a Django User.
    Billing address is permanent and stored here.
    Service address will be handled dynamically per session.
    """

    # 🔗 User association
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="registered_customer_profile",
        null=True,
        blank=True,
    )

    # 🆔 Unique ID for external references (e.g., invoices, Stripe)
    unique_customer_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    # 👤 Personal Info
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)

    # 💳 Billing Address (permanent)
    billing_street_address = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=50, blank=True)
    billing_zipcode = models.CharField(max_length=20, blank=True)

    # 🌍 Region / country for filtering or tax logic
    region = models.CharField(max_length=100, default="Unknown")

    # 📅 Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registered Customer"
        verbose_name_plural = "Registered Customers"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.billing_city or 'No city'})"

    # ---------------------------------------------------
    # 🧾 Utility Properties
    # ---------------------------------------------------
    @property
    def full_billing_address(self):
        """Returns a formatted single-line billing address."""
        parts = [
            self.billing_street_address,
            self.billing_city,
            self.billing_state,
            self.billing_zipcode,
        ]
        return ", ".join(filter(None, parts))

    def has_valid_billing_address(self) -> bool:
        """Quick validation check for completeness."""
        return all([
            self.billing_street_address.strip() if self.billing_street_address else None,
            self.billing_city.strip() if self.billing_city else None,
            self.billing_state.strip() if self.billing_state else None,
            self.billing_zipcode.strip() if self.billing_zipcode else None,
        ])
