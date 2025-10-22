# billing/forms.py
from django import forms


class CheckoutForm(forms.Form):
    """Checkout form collecting billing address info (prefilled if logged in)."""

    billing_name = forms.CharField(
        label="Full Name",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    billing_street_address = forms.CharField(
        label="Street Address",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    billing_city = forms.CharField(
        label="City",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    billing_state = forms.CharField(
        label="State / Province",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    billing_zipcode = forms.CharField(
        label="ZIP / Postal Code",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    billing_country = forms.CharField(
        label="Country",
        max_length=50,
        initial="USA",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        """Prefill from user's RegisteredCustomer profile, if available."""
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if not user or not user.is_authenticated:
            return  # guest checkout (shouldn’t normally happen)

        rc = getattr(user, "registered_customer_profile", None)
        if not rc:
            return

        # Prefill values safely
        self.fields["billing_name"].initial = f"{rc.first_name} {rc.last_name}".strip(
        )
        self.fields["billing_street_address"].initial = rc.billing_street_address or ""
        self.fields["billing_city"].initial = rc.billing_city or ""
        self.fields["billing_state"].initial = rc.billing_state or ""
        self.fields["billing_zipcode"].initial = rc.billing_zipcode or ""
        self.fields["billing_country"].initial = getattr(rc, "region", "USA")
