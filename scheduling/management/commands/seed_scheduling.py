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
    help = "Seed scheduling data using RegisteredCustomers (Bookings, Employees, etc.)"

    def handle(self, *args, **kwargs):
        # 🧹 Clear old data
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
        slot_objs = {label: TimeSlot.objects.create(
            label=label) for label in slot_labels}
        self.stdout.write(self.style.SUCCESS("✅ Time slots created."))

        # 🔹 Employees
        employees = []
        for category_name, category_obj in category_objs.items():
            for _ in range(5):
                emp = Employee.objects.create(
                    name=fake.name(),
                    home_address=random.choice(DALLAS_ADDRESSES),
                    service_category=category_obj,
                )
                employees.append(emp)
        self.stdout.write(self.style.SUCCESS("✅ Employees seeded."))

        # 🔹 Registered customers
        registered_customers = list(RegisteredCustomer.objects.all())
        use_customers = len(registered_customers) > 0
        if not use_customers:
            self.stdout.write(self.style.WARNING(
                "⚠️ No RegisteredCustomers found, using fallback addresses."))

        today = timezone.now().date()
        total_bookings = 0

        for day in range(28):
            booking_date = today + timedelta(days=day)

            for category_name, category_obj in category_objs.items():
                category_emps = list(Employee.objects.filter(
                    service_category=category_obj))
                random.shuffle(category_emps)
                reserved_free_emp = category_emps.pop()  # keep one free each day

                for slot_label, slot_obj in slot_objs.items():
                    if random.random() < 0.2:  # 20% slot utilization
                        if use_customers:
                            cust = random.choice(registered_customers)
                            addr_parts = [
                                cust.billing_street_address,
                                cust.billing_city,
                                cust.billing_state,
                                cust.billing_zipcode,
                            ]
                            service_address = ", ".join(
                                p for p in addr_parts if p) or random.choice(DALLAS_ADDRESSES)
                            booking = Booking.objects.create(
                                user=cust.user,
                                service_address=service_address,
                                service_category=category_obj,
                                date=booking_date,
                                time_slot=slot_obj,
                                status="active",
                            )
                        else:
                            service_address = random.choice(DALLAS_ADDRESSES)
                            booking = Booking.objects.create(
                                service_address=service_address,
                                service_category=category_obj,
                                date=booking_date,
                                time_slot=slot_obj,
                                status="active",
                            )

                        # Assign an employee (not the reserved one)
                        available_emps = [
                            e for e in category_emps if e != reserved_free_emp]
                        if available_emps:
                            emp = random.choice(available_emps)
                            JobAssignment.objects.create(
                                employee=emp,
                                booking=booking,
                                jobsite_address=booking.service_address,
                            )

                        total_bookings += 1

        msg = (
            f"✅ Bookings + assignments seeded: {total_bookings} "
            f"({'RegisteredCustomers' if use_customers else 'fallback addresses'})"
        )
        self.stdout.write(self.style.SUCCESS(msg))
