from django import forms
from django.core.exceptions import ObjectDoesNotExist
from .models import ServiceCategory, TimeSlot
from customers.models import RegisteredCustomer


class SearchByDateForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    customer_address = forms.CharField(max_length=255, label="Service Address")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            try:
                rc = user.registeredcustomer
                if rc.address:
                    self.fields["customer_address"].initial = rc.address
            except ObjectDoesNotExist:
                pass


class SearchByTimeSlotForm(forms.Form):
    time_slot = forms.ModelChoiceField(queryset=None)
    customer_address = forms.CharField(max_length=255, label="Service Address")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        from scheduling.models import TimeSlot
        self.fields["time_slot"].queryset = TimeSlot.objects.all()

        if user and user.is_authenticated:
            try:
                rc = user.registered_customer_profile
                if rc.address:
                    self.fields["customer_address"].initial = rc.address
            except ObjectDoesNotExist:
                pass
