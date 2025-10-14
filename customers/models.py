from django.db import models

# Create your models here.


class RegisteredCustomer(models.Model):
    unique_customer_id = models.UUIDField(primary_key=False, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zipcode = models.CharField(max_length=20)
    phone = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    region = models.CharField(max_length=100, default="Unknown")  # ✅ new field

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.city})"
