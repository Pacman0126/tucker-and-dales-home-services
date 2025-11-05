# customers/admin.py
from django.contrib import admin
from customers.models import CustomerProfile


# Register your models here.
@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "billing_city", "billing_state", "region", "phone")
    search_fields = ("user__username", "user__email",
                     "billing_city", "billing_state", "company", "phone")
