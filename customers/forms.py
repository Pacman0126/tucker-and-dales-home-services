from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import RegisteredCustomer


# ==============================================================
# 🔐 Login or Register (hybrid form)
# ==============================================================
class LoginOrRegisterForm(UserCreationForm):
    """
    Registration/login hybrid form.
    - Allows existing usernames/emails (uniqueness handled in the view)
    - Keeps Django’s password validation & field normalization
    """

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email address",
                "autocomplete": "email",
            }
        ),
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "First name",
                "autocomplete": "given-name",
            }
        ),
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Last name",
                "autocomplete": "family-name",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Username",
                    "autocomplete": "username",
                }
            ),
        }

    def clean_username(self):
        """Disable built-in unique username enforcement (handled in view)."""
        username = self.cleaned_data.get("username", "").strip()
        return username

    def clean_email(self):
        """Normalize email without enforcing uniqueness."""
        return self.cleaned_data.get("email", "").strip().lower()

    def validate_unique(self):
        """Bypass default unique constraint validation."""
        pass


# ==============================================================
# 🧾 Customer Profile / Billing Info Form
# ==============================================================
class CustomerProfileForm(forms.ModelForm):
    """
    Allows updating billing address, phone, and email.
    Service address will be handled per session (not stored here).
    """

    class Meta:
        model = RegisteredCustomer
        fields = [
            "email",
            "phone",
            "billing_street_address",
            "billing_city",
            "billing_state",
            "billing_zipcode",
        ]

        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Email address",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Phone number",
                }
            ),
            "billing_street_address": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Street address",
                }
            ),
            "billing_city": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "City",
                }
            ),
            "billing_state": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "State",
                }
            ),
            "billing_zipcode": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "ZIP / Postal Code",
                }
            ),
        }

    def clean_email(self):
        """Ensure non-empty, normalized email."""
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise forms.ValidationError("Email address is required.")
        return email
