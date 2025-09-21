from django.db import models

# Create your models here.


class RegisteredCustomer(models.Model):
    unique_customer_id = models.CharField(max_length=36, unique=True)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    street_address = models.CharField(max_length=120)
    city = models.CharField(max_length=60)
    state = models.CharField(max_length=30)
    zipcode = models.CharField(max_length=15)
    phone = models.CharField(max_length=25)
    email = models.EmailField(unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
