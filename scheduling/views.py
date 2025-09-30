from django.shortcuts import render
from datetime import date, timedelta

from .forms import SearchByDateForm, SearchByTimeSlotForm
from .availability import get_available_employees


def search_by_date(request):
    """
    Customer selects a date → show all time slots that day,
    with available employees for the chosen service category.
    """
    form = SearchByDateForm(request.GET or None)
    results = None

    if form.is_valid():
        selected_date = form.cleaned_data["date"]
        category = form.cleaned_data["service_category"]
        customer_address = form.cleaned_data["customer_address"]

        # Standard slots (seeded consistently in DB)
        slots = ["7:30-9:30", "10:00-12:00", "12:30-2:30", "3:00-5:00"]

        results = {
            slot: get_available_employees(
                customer_address,
                selected_date,
                slot,
                category,
            )
            for slot in slots
        }

    return render(
        request,
        "scheduling/search_by_date.html",
        {"form": form, "results": results},
    )


def search_by_time_slot(request):
    """
    Customer selects a time slot → show all days (next 28 days)
    where employees are available in that slot for the chosen service.
    """
    form = SearchByTimeSlotForm(request.GET or None)
    results = None

    if form.is_valid():
        slot = form.cleaned_data["time_slot"]
        category = form.cleaned_data["service_category"]
        customer_address = form.cleaned_data["customer_address"]

        today = date.today()
        days = [today + timedelta(days=i) for i in range(28)]

        results = {
            day: get_available_employees(
                customer_address,
                day,
                slot,
                category,
            )
            for day in days
        }

    return render(
        request,
        "scheduling/search_by_time_slot.html",
        {"form": form, "results": results},
    )
