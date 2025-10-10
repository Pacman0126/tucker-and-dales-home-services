from django import forms
from .models import ServiceCategory, TimeSlot


class SearchByDateForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control",
        })
    )
    service_category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    customer_address = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your address",
        })
    )


class SearchByTimeSlotForm(forms.Form):
    time_slot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Select a time slot",
    )

    service_category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,            # ✅ optional now
        empty_label="All Categories",  # ✅ safe default
    )

    customer_address = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your address",
        })
    )
