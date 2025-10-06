import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from scheduling.models import ServiceCategory, Employee, TimeSlot, Booking, JobAssignment
from customers.models import RegisteredCustomer

fake = Faker()

# 🔹 Dallas-area fallback addresses (only used if no RegisteredCustomers exist)
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


class Command(BaseCommand):
    help = "Seed scheduling app with service categories, employees, timeslots, and bookings (using only RegisteredCustomers)."

    def handle(self, *args, **kwargs):
        # 🔹 Clear old data
        JobAssignment.objects.all().delete()
        Booking.objects.all().delete()
        Employee.objects.all().delete()
        TimeSlot.objects.all().delete()
        ServiceCategory.objects.all().delete()

        self.stdout.write(self.style.WARNING("🧹 Old scheduling data cleared."))

        # 🔹 Create service categories
        categories = ["Garage/Basement", "Lawncare", "House Cleaning"]
        category_objs = {
            name: ServiceCategory.objects.create(name=name) for name in categories
        }
        self.stdout.write(self.style.SUCCESS("✅ Service categories created."))

        # 🔹 Create time slots
        slot_labels = ["7:30-9:30", "10:00-12:00", "12:30-2:30", "3:00-5:00"]
        slot_objs = {label: TimeSlot.objects.create(
            label=label) for label in slot_labels}
        self.stdout.write(self.style.SUCCESS("✅ Time slots created."))

        # 🔹 Seed employees (5 per category)
        employees = []
        for category_name, category_obj in category_objs.items():
            for _ in range(5):
                emp = Employee.objects.create(
                    name=fake.name(),
                    home_address=random.choice(DALLAS_ADDRESSES),
                    service_category=category_obj,
                )
                employees.append(emp)
        self.stdout.write(
            self.style.SUCCESS(
                "✅ Employees seeded with Dallas-area home addresses.")
        )

        # 🔹 Fetch RegisteredCustomers
        registered_customers = list(RegisteredCustomer.objects.all())
        use_customers = len(registered_customers) > 0

        if not use_customers:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️ No RegisteredCustomers found, falling back to Metroplex addresses."
                )
            )

        # 🔹 Seed bookings for next 28 days
        today = timezone.now().date()
        total_bookings = 0

        for day in range(28):
            booking_date = today + timedelta(days=day)

            for category_name, category_obj in category_objs.items():
                category_emps = list(
                    Employee.objects.filter(service_category=category_obj)
                )
                random.shuffle(category_emps)

                # Reserve 1 employee to ALWAYS remain free for this category/day
                reserved_free_emp = category_emps.pop()

                for slot_label, slot_obj in slot_objs.items():
                    if random.random() < 0.2:  # 20% chance slot has a booking
                        if use_customers:
                            cust = random.choice(registered_customers)
                            customer_name = f"{cust.first_name} {cust.last_name}"
                            customer_address = (
                                f"{cust.street_address}, {cust.city}, {cust.state} {cust.zipcode}"
                            )
                        else:
                            customer_name = fake.name()
                            customer_address = random.choice(DALLAS_ADDRESSES)

                        booking = Booking.objects.create(
                            customer_name=customer_name,
                            customer_address=customer_address,
                            service_category=category_obj,
                            date=booking_date,
                            time_slot=slot_obj,
                        )

                        # Assign exactly 1 employee (not the reserved free one)
                        available_emps = [
                            e for e in category_emps if e != reserved_free_emp]
                        if available_emps:
                            emp = random.choice(available_emps)
                            JobAssignment.objects.create(
                                employee=emp,
                                booking=booking,
                                jobsite_address=booking.customer_address,
                            )

                        total_bookings += 1

        if use_customers:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Bookings + assignments seeded: {total_bookings} (from {len(registered_customers)} RegisteredCustomers)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Bookings + assignments seeded: {total_bookings} (fallback Dallas-area addresses)."
                )
            )
