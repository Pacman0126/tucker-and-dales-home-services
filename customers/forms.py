from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


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
        """
        Disable built-in unique username enforcement.
        Let the view decide whether to log in or create a new user.
        """
        username = self.cleaned_data.get("username", "").strip()
        return username

    def clean_email(self):
        """
        Normalize email without enforcing uniqueness.
        """
        return self.cleaned_data.get("email", "").strip().lower()

    def validate_unique(self):
        """
        Override the model’s unique-field checks entirely.
        (Django calls this during ModelForm.save())
        """
        # Intentionally skip uniqueness validation
        return
