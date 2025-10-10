import datetime
from django.shortcuts import render
from django.conf import settings
from scheduling.models import TimeSlot, ServiceCategory
from .forms import SearchByDateForm, SearchByTimeSlotForm
from .availability import get_available_employees


def search_by_date(request):
    form = SearchByDateForm(request.GET or None)
    results = None

    if form.is_valid():
        date = form.cleaned_data["date"]
        customer_address = form.cleaned_data["customer_address"]

        # Fetch all time slots and all service categories
        slots = TimeSlot.objects.all().order_by("id")
        categories = ServiceCategory.objects.all()

        results = {}
        for slot in slots:
            # For each slot, build category-based availability
            day_results = {}
            for category in categories:
                employees = get_available_employees(
                    customer_address=customer_address,
                    date=date,
                    time_slot=slot,
                    service_category=category,
                )
                day_results[category] = employees
            results[slot] = day_results

        print(f"✅ DEBUG: Date={date} Results={len(results)} slots checked")

    else:
        print(f"❌ DEBUG: Invalid form errors={form.errors}")

    return render(
        request,
        "scheduling/search_by_date.html",
        {
            "form": form,
            "results": results,
            "GOOGLE_MAPS_BROWSER_KEY": settings.GOOGLE_MAPS_BROWSER_KEY,
        },
    )

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
        customer_address = form.cleaned_data["customer_address"]

        # ✅ We're no longer selecting a category — we’ll include all categories automatically
        results = {}
        today = datetime.date.today()
        days = [today + datetime.timedelta(days=i) for i in range(28)]

        # Iterate over all categories, same as pre-refactor
        all_categories = ServiceCategory.objects.all()

        for day in days:
            results[day] = {}
            for category in all_categories:
                results[day][category.name] = get_available_employees(
                    customer_address=customer_address,
                    date=day,
                    time_slot=slot,
                    service_category=category,
                )

        print(
            f"✅ DEBUG: VALID FORM slot={slot} addr={customer_address} results={len(results)}")

    else:
        print(f"❌ DEBUG: INVALID FORM — errors={form.errors}")

    return render(
        request,
        "scheduling/search_by_time_slot.html",
        {
            "form": form,
            "results": results,
            "time_slots": TimeSlot.objects.all(),
            "GOOGLE_MAPS_BROWSER_KEY": settings.GOOGLE_MAPS_BROWSER_KEY,
        },
    )


def choose_search(request):
    return render(request, "scheduling/choose_search.html")
