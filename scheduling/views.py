from django.shortcuts import render
from .forms import SearchByDateForm, SearchByTimeSlotForm
from .availability import get_available_employees
from .models import Booking

# Create your views here.


def search_by_date(request):
    form = SearchByDateForm(request.GET or None)
    results = None
    if form.is_valid():
        date = form.cleaned_data["date"]
        category = form.cleaned_data["service_category"]
        # For each time slot, find available employees
        slots = ["7:30-9:30", "10:00-12:00", "12:30-2:30", "3:00-5:00"]
        results = {
            slot: get_available_employees(
                request.GET.get("customer_address", ""),
                date,
                slot,
                category,
            )
            for slot in slots
        }  # a dictionary comprehension
    return render(request, "scheduling/search_by_date.html", {"form": form, "results": results})


def search_by_time_slot(request):
    form = SearchByTimeSlotForm(request.GET or None)
    results = None
    if form.is_valid():
        slot = form.cleaned_data["time_slot"]
        category = form.cleaned_data["service_category"]
        # For each day this week, show employees
        import datetime
        today = datetime.date.today()
        days = [today + datetime.timedelta(days=i) for i in range(6)]
        results = {
            day: get_available_employees(
                request.GET.get("customer_address", ""),
                day,
                slot,
                category,
            )
            for day in days
        }  # a dictionary comprehension
    return render(request, "scheduling/search_by_time_slot.html", {"form": form, "results": results})
