from django import forms
from customers.models import RegisteredCustomer


class CheckoutForm(forms.Form):
    billing_name = forms.CharField(label="Full Name", max_length=100)
    billing_address = forms.CharField(label="Billing Address", max_length=255)
    city = forms.CharField(label="City", max_length=100)
    postal_code = forms.CharField(label="Postal Code", max_length=20)
    country = forms.CharField(label="Country", max_length=50, initial="USA")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            try:
                rc = user.registered_customer_profile
                if rc.billing_address:
                    self.fields["billing_address"].initial = rc.billing_address
                    self.fields["city"].initial = rc.billing_city
                    self.fields["postal_code"].initial = rc.billing_postal_code
                    self.fields["country"].initial = getattr(
                        rc, "billing_country", "USA")
                    self.fields["billing_name"].initial = f"{user.first_name} {user.last_name}".strip(
                    )
            except RegisteredCustomer.DoesNotExist:
                pass
