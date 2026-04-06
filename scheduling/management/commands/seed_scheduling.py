import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from scheduling.models import (
    ServiceCategory,
    Employee,
    TimeSlot,
    Booking,
    JobAssignment,
)
from customers.models import CustomerProfile


# 🔹 Dallas-area fallback addresses
# Only used if a profile has missing address data.
DALLAS_ADDRESSES = [
    "123 Greenville Ave, Dallas, TX 75206",
    "1400 Pacific Ave, Dallas, TX 75202",
    "3500 Oak Lawn Ave, Dallas, TX 75219",
    "5600 Ross Ave, Dallas, TX 75206",
    "3900 Gaston Ave, Dallas, TX 75246",
    "8100 Preston Rd, Plano, TX 75024",
    "2100 W Walnut St, Garland, TX 75042",
    "3000 N Belt Line Rd, Irving, TX 75062",
    "1000 Ballpark Way, Arlington, TX 76011",
    "1155 Union Cir, Denton, TX 76203",
    "1900 E Belt Line Rd, Carrollton, TX 75006",
    "2601 Preston Rd, Frisco, TX 75034",
    "1100 Long Prairie Rd, Flower Mound, TX 75028",
    "400 W Campbell Rd, Richardson, TX 75080",
]

# 🔹 Make the schedule busier
SLOT_UTILIZATION = 0.35


def profile_full_address(profile: CustomerProfile) -> str:
    parts = [
        (profile.billing_street_address or "").strip(),
        (profile.billing_city or "").strip(),
        (profile.billing_state or "").strip(),
        (profile.billing_zipcode or "").strip(),
    ]
    return ", ".join([p for p in parts if p])


def profile_full_name(profile: CustomerProfile) -> str:
    first = (profile.user.first_name or "").strip()
    last = (profile.user.last_name or "").strip()
    full_name = f"{first} {last}".strip()
    return full_name or profile.user.username


class Command(BaseCommand):
    help = (
        "Seed 120 days of scheduling data using restored CustomerProfiles, "
        "with 15 employees drawn from the preserved user pool."
    )

    def handle(self, *args, **kwargs):
        # 🧹 Clear scheduling-only data
        JobAssignment.objects.all().delete()
        Booking.objects.all().delete()
        Employee.objects.all().delete()
        TimeSlot.objects.all().delete()
        ServiceCategory.objects.all().delete()
        self.stdout.write(self.style.WARNING("🧹 Old scheduling data cleared."))

        # 🔹 Service categories
        categories = ["Garage/Basement", "Lawncare", "House Cleaning"]
        category_objs = {
            name: ServiceCategory.objects.create(name=name)
            for name in categories
        }
        self.stdout.write(self.style.SUCCESS("✅ Service categories created."))

        # 🔹 Time slots
        slot_labels = ["7:30–9:30", "10:00–12:00", "12:30–2:30", "3:00–5:00"]
        slot_objs = {
            label: TimeSlot.objects.create(label=label)
            for label in slot_labels
        }
        self.stdout.write(self.style.SUCCESS("✅ Time slots created."))

        # 🔹 Restored customer profiles
        customer_profiles = list(
            CustomerProfile.objects.select_related("user").order_by("user__id")
        )

        if not customer_profiles:
            raise ValueError(
                ("No CustomerProfile records found. "
                 "Restore customer profiles first.")
            )

        if len(customer_profiles) < 15:
            raise ValueError(
                "Need at least 15 CustomerProfiles to draw "
                "employees from the user pool. "
                f"Current count: {len(customer_profiles)}"
            )

        # 🔹 Draw 15 employees from the user pool
        employee_source_profiles = random.sample(customer_profiles, 15)

        employees_by_category = {name: [] for name in categories}
        source_index = 0

        for category_name in categories:
            category_obj = category_objs[category_name]

            for _ in range(5):
                profile = employee_source_profiles[source_index]
                source_index += 1

                employee = Employee.objects.create(
                    name=profile_full_name(profile),
                    home_address=profile_full_address(
                        profile) or random.choice(DALLAS_ADDRESSES),
                    service_category=category_obj,
                )
                employees_by_category[category_name].append(employee)

        self.stdout.write(
            self.style.SUCCESS(
                "✅ 15 employees created from the preserved user pool.")
        )

        today = timezone.now().date()
        total_bookings = 0
        total_assignments = 0

        # 🔹 120-day scheduling horizon
        for day in range(120):
            booking_date = today + timedelta(days=day)

            for category_name, category_obj in category_objs.items():
                category_emps = list(employees_by_category[category_name])
                random.shuffle(category_emps)

                # Keep one employee free each day in each category
                reserved_free_emp = category_emps.pop()
                available_emps = [
                    e for e in category_emps if e != reserved_free_emp]

                for slot_label, slot_obj in slot_objs.items():
                    if random.random() < SLOT_UTILIZATION:
                        cust = random.choice(customer_profiles)
                        service_address = profile_full_address(
                            cust) or random.choice(DALLAS_ADDRESSES)

                        assigned_emp = random.choice(available_emps)

                        booking = Booking.objects.create(
                            user=cust.user,
                            service_address=service_address,
                            service_category=category_obj,
                            date=booking_date,
                            time_slot=slot_obj,
                            employee=assigned_emp,
                            status="Booked",
                        )

                        JobAssignment.objects.create(
                            employee=assigned_emp,
                            booking=booking,
                            jobsite_address=booking.service_address,
                        )

                        total_bookings += 1
                        total_assignments += 1

        msg = (
            f"✅ Bookings + assignments seeded: {total_bookings} bookings, "
            f"{total_assignments} assignments, 15 employees drawn "
            "from restored CustomerProfiles, "
            f"120-day horizon, utilization={SLOT_UTILIZATION:.0%}."
        )
        self.stdout.write(self.style.SUCCESS(msg))
