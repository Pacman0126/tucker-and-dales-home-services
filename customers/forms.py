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
                "class": "form-control mb-3",
                "placeholder": "First name",
                "autocomplete": "given-name",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control mb-3",
                "placeholder": "Last name",
                "autocomplete": "family-name",
            }),
            "street_address": forms.TextInput(attrs={
                "class": "form-control mb-3",
                "placeholder": "Street address",
                "autocomplete": "address-line1",
            }),
            "city": forms.TextInput(attrs={
                "class": "form-control mb-3",
                "placeholder": "City",
                "autocomplete": "address-level2",
            }),
            "state": forms.TextInput(attrs={
                "class": "form-control mb-3",
                "placeholder": "State",
                "autocomplete": "address-level1",
            }),
            "zipcode": forms.TextInput(attrs={
                "class": "form-control mb-3",
                "placeholder": "Zipcode",
                "autocomplete": "postal-code",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control mb-3",
                "placeholder": "Phone number",
                "autocomplete": "tel",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control mb-3",
                "placeholder": "Email address",
                "autocomplete": "email",
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
                "Email must be valid and end with .com, .net, or .org."
            )
        return e
