from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from customers.models import CustomerProfile


# ==============================================================
# 🔐 Login or Register (hybrid form)
# ==============================================================
class LoginOrRegisterForm(UserCreationForm):
    """
    Registration/login hybrid form.
    - Allows existing usernames/emails (uniqueness handled in the view)
    - Keeps Django's password validation & field normalization
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
        return self.cleaned_data.get("username", "").strip()

    def clean_email(self):
        """Normalize email without enforcing uniqueness."""
        return self.cleaned_data.get("email", "").strip().lower()

    def validate_unique(self):
        """Bypass default unique constraint validation; handled in the view."""
        pass


# ==============================================================
# 🧾 Customer Profile / Billing Info Form
# ==============================================================
class CustomerProfileForm(forms.ModelForm):
    """
    Canonical CustomerProfile form.
    Stores contact + billing + optional service snapshot fields.
    First/last name remain on Django's User model, not CustomerProfile.
    """

    class Meta:
        model = CustomerProfile
        fields = [
            "email",
            "phone",
            "company",
            "preferred_contact",
            "timezone",
            "billing_street_address",
            "billing_city",
            "billing_state",
            "billing_zipcode",
            "region",
            "service_street_address",
            "service_city",
            "service_state",
            "service_zipcode",
            "service_region",
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
                    "placeholder": "Phone number (required)",
                    "autocomplete": "tel",
                    "required": "required",
                }
            ),
            "company": forms.TextInput(
                attrs={"class": "form-control mb-2", "placeholder": "Company"}
            ),
            "preferred_contact": forms.Select(
                attrs={"class": "form-select mb-2"}
            ),
            "timezone": forms.TextInput(
                attrs={"class": "form-control mb-2", "placeholder": "Timezone"}
            ),
            "billing_street_address": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Billing street address",
                }
            ),
            "billing_city": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Billing city",
                }
            ),
            "billing_state": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Billing state",
                }
            ),
            "billing_zipcode": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Billing ZIP / Postal Code",
                }
            ),
            "region": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Billing country / region code",
                }
            ),
            "service_street_address": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Service street address",
                }
            ),
            "service_city": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Service city",
                }
            ),
            "service_state": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Service state",
                }
            ),
            "service_zipcode": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Service ZIP / Postal Code",
                }
            ),
            "service_region": forms.TextInput(
                attrs={
                    "class": "form-control mb-2",
                    "placeholder": "Service country / region code",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["phone"].required = True
        self.fields["phone"].help_text = (
            "Required so staff can contact you about scheduled services."
        )

    def clean_email(self):
        """Ensure non-empty, normalized email."""
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise forms.ValidationError("Email address is required.")
        return email

    def clean_phone(self):
        """Require phone number for operational contact."""
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone:
            raise forms.ValidationError(
                "Phone number is required so staff can contact you."
            )
        return phone
