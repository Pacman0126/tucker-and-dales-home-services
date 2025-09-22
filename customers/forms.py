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
            "first_name": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "First name"
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Last name"
            }),
            "street_address": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Street address"
            }),
            "city": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "City"
            }),
            "state": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "State"
            }),
            "zipcode": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Zipcode"
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Phone number"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control", "placeholder": "Email address"
            }),
        }

    def clean_phone(self):
        p = self.cleaned_data.get("phone", "").strip()
        if not any(ch.isdigit() for ch in p):
            raise forms.ValidationError("Phone number must include digits.")
        return p

    def clean_email(self):
        e = self.cleaned_data.get("email", "").strip()
        if e and not e.endswith((".com", ".net", ".org")):  # simple example rule
            raise forms.ValidationError(
                "Email must be valid and end with .com, .net, or .org.")
        return e
