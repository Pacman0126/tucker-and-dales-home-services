from django.shortcuts import render
from django.conf import settings
from .forms import SearchByDateForm, SearchByTimeSlotForm
from .availability import get_available_employees
from .models import TimeSlot
import datetime


def search_by_date(request):
    form = SearchByDateForm(request.GET or None)
    results = None
    if form.is_valid():
        date = form.cleaned_data["date"]
        category = form.cleaned_data["service_category"]
        customer_address = form.cleaned_data["customer_address"]

        # For each time slot, find available employees
        slots = TimeSlot.objects.all().order_by("id")
        results = {
            slot: get_available_employees(
                customer_address,
                date,
                slot,
                category,
            )
            for slot in slots
        }

    return render(
        request,
        "scheduling/search_by_date.html",
        {
            "form": form,
            "results": results,
            "GOOGLE_MAPS_BROWSER_KEY": settings.GOOGLE_MAPS_BROWSER_KEY,
        },
    )


def search_by_time_slot(request):
    form = SearchByTimeSlotForm(request.GET or None)
    results = None

    if form.is_valid():
        slot = form.cleaned_data["time_slot"]
        category = form.cleaned_data["service_category"]
        customer_address = form.cleaned_data["customer_address"]

        if slot:
            today = datetime.date.today()
            days = [today + datetime.timedelta(days=i) for i in range(28)]

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
        {
            "form": form,
            "results": results,
            # ✅ pass correct variable name expected by template
            "GOOGLE_MAPS_BROWSER_KEY": settings.GOOGLE_MAPS_BROWSER_KEY,
        },
    )
