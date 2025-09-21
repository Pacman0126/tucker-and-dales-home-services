from django import forms
from .models import RegisteredCustomer


class RegisteredCustomerForm(forms.ModelForm):
    class Meta:
        model = RegisteredCustomer
        fields = [
            "unique_customer_id", "first_name", "last_name",
            "street_address", "city", "state", "zipcode",
            "phone", "email",
        ]

    def clean_phone(self):
        p = self.cleaned_data["phone"]
        if not any(ch.isdigit() for ch in p):
            raise forms.ValidationError("Phone number must include digits.")
        return p
