from scheduling.models import TimeSlot
from django import forms
from django.core.exceptions import ObjectDoesNotExist

from customers.models import RegisteredCustomer
from .models import ServiceCategory, TimeSlot


class SearchByDateForm(forms.Form):
    """
    Search employees by date for a specific address.
    - Address optional (session lock takes priority)
    """
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Service Date"
    )
    customer_address = forms.CharField(
        max_length=255,
        label="Service Address",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        locked_address = kwargs.pop("locked_address", None)
        super().__init__(*args, **kwargs)

        # Prepopulate if address locked in session
        if locked_address:
            self.fields["customer_address"].initial = locked_address

        # Fallback to profile billing address if logged in
        elif user and user.is_authenticated:
            rc = getattr(user, "registered_customer_profile", None)
            if rc and getattr(rc, "billing_street_address", None):
                self.fields["customer_address"].initial = rc.billing_street_address


class SearchByTimeSlotForm(forms.Form):
    """
    Search by time slot (across 28 days).
    - Address optional (session lock takes priority)
    """
    time_slot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.all(),
        label="Select Time Slot"
    )
    customer_address = forms.CharField(
        max_length=255,
        label="Service Address",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        locked_address = kwargs.pop("locked_address", None)
        super().__init__(*args, **kwargs)

        if locked_address:
            self.fields["customer_address"].initial = locked_address
        elif user and user.is_authenticated:
            rc = getattr(user, "registered_customer_profile", None)
            if rc and getattr(rc, "billing_street_address", None):
                self.fields["customer_address"].initial = rc.billing_street_address
