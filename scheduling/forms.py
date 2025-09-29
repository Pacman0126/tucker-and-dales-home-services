from django import forms
from .models import ServiceCategory

TIME_SLOTS = [
    ("7:30-9:30", "7:30 – 9:30"),
    ("10:00-12:00", "10:00 – 12:00"),
    ("12:30-2:30", "12:30 – 2:30"),
    ("3:00-5:00", "3:00 – 5:00"),
]


class SearchByDateForm(forms.Form):
    date = forms.DateField(widget=forms.SelectDateWidget)
    service_category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.all())


class SearchByTimeSlotForm(forms.Form):
    time_slot = forms.ChoiceField(choices=TIME_SLOTS)
    service_category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.all())
