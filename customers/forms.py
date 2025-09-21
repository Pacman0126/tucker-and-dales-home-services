from django import forms
from .models import RegisteredCustomer


class RegisteredCustomerForm(forms.ModelForm):
    class Meta:
        model = RegisteredCustomer
        fields = [
            "first_name",
            "last_name",
            "street_address",
            "city",
            "state",
            "zipcode",
            "phone",
            "email",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "street_address": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "zipcode": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def clean_phone(self):
        p = self.cleaned_data["phone"]
        if not any(ch.isdigit() for ch in p):
            raise forms.ValidationError("Phone number must include digits.")
        return p
