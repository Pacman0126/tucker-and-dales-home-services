from django.db import models

# Create your models here.


import uuid
from django.db import models
from django.contrib.auth.models import User


class RegisteredCustomer(models.Model):
    # 🔗 Link each customer record to a Django User account
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="registered_customer_profile",
        null=True,  # allow null for backward compatibility
        blank=True
    )

    # 🆔 Keep your existing UUID for cross-referencing (e.g., invoices)
    unique_customer_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    # 👤 Customer Info
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    # 🏠 Address
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zipcode = models.CharField(max_length=20)

    # ☎️ Contact
    phone = models.CharField(max_length=30)
    email = models.EmailField(unique=True)

    # 🌍 Additional Info
    region = models.CharField(max_length=100, default="Unknown")

    # 📅 Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registered Customer"
        verbose_name_plural = "Registered Customers"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.city})"
