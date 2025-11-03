from django.db import models
from django.contrib.auth import get_user_model

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
