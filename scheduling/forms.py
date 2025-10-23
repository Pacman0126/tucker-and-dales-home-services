from scheduling.models import TimeSlot
from django import forms
from django.core.exceptions import ObjectDoesNotExist

from customers.models import RegisteredCustomer
from .models import ServiceCategory, TimeSlot


class SearchByDateForm(forms.Form):
    """
    Lets users search available employees by a specific date and address.
    Prefills service address from the user's billing info if logged in.
    """
    date = forms.DateField(
        label="Select Date",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )

    customer_address = forms.CharField(
        max_length=255,
        label="Service Address",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # ✅ Prefill from registered customer profile
        if user and user.is_authenticated:
            try:
                rc = user.registered_customer_profile
                if hasattr(rc, "billing_street_address"):
                    full_address = ", ".join(
                        filter(None, [
                            rc.billing_street_address,
                            rc.billing_city,
                            rc.billing_state,
                            rc.billing_zipcode,
                        ])
                    )
                    if full_address:
                        self.fields["customer_address"].initial = full_address
            except ObjectDoesNotExist:
                pass


class SearchByTimeSlotForm(forms.Form):
    """
    Lets users search for available employees by time slot (across next 28 days).
    Prefills service address from the user's billing info if logged in.
    """
    time_slot = forms.ModelChoiceField(
        label="Time Slot",
        queryset=TimeSlot.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"})
    )

    customer_address = forms.CharField(
        max_length=255,
        label="Service Address",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # ✅ Safe queryset assignment (type-checker friendly)
        self.fields["time_slot"].queryset = TimeSlot.objects.all()

        # ✅ Prefill address from RegisteredCustomer billing info
        if user and user.is_authenticated:
            try:
                rc = user.registered_customer_profile
                if hasattr(rc, "billing_street_address"):
                    full_address = ", ".join(
                        filter(None, [
                            rc.billing_street_address,
                            rc.billing_city,
                            rc.billing_state,
                            rc.billing_zipcode,
                        ])
                    )
                    if full_address:
                        self.fields["customer_address"].initial = full_address
            except ObjectDoesNotExist:
                pass
