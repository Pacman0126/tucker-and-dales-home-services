import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from faker import Faker

from scheduling.models import ServiceCategory, Employee, TimeSlot, Booking, JobAssignment

fake = Faker()

# 🔹 Dallas-area addresses for more realistic jobsites
DALLAS_ADDRESSES = [
    "123 Greenville Ave, Dallas, TX 75206",
    "2500 Cedar Springs Rd, Dallas, TX 75201",
    "7800 N Stemmons Fwy, Dallas, TX 75247",
    "4000 Cedar Springs Rd, Dallas, TX 75219",
    "1400 Pacific Ave, Dallas, TX 75202",
    "100 Highland Park Village, Dallas, TX 75205",
    "4500 Harry Hines Blvd, Dallas, TX 75219",
    "6000 Preston Rd, Dallas, TX 75205",
    "1234 Lovers Ln, Dallas, TX 75225",
    "8900 Hillcrest Rd, Dallas, TX 75225",
    "3500 Oak Lawn Ave, Dallas, TX 75219",
    "2200 N Pearl St, Dallas, TX 75201",
    "4100 Lomo Alto Dr, Dallas, TX 75219",
    "7000 Mockingbird Ln, Dallas, TX 75214",
    "10200 E Northwest Hwy, Dallas, TX 75238",
    "5600 Ross Ave, Dallas, TX 75206",
    "3900 Gaston Ave, Dallas, TX 75246",
    "12200 Preston Rd, Dallas, TX 75230",
    "4800 W Lovers Ln, Dallas, TX 75209",
    "9999 Forest Ln, Dallas, TX 75243",
]


class Command(BaseCommand):
    help = "Seed scheduling app with service categories, employees, timeslots, and bookings for 28 days (Dallas-area realistic addresses)."

    def handle(self, *args, **kwargs):
        # 🔹 Fully clear and reset IDs
        with connection.cursor() as cursor:
            cursor.execute("""
                TRUNCATE TABLE 
                    scheduling_jobassignment,
                    scheduling_booking,
                    scheduling_employee,
                    scheduling_servicecategory,
                    scheduling_timeslot
                RESTART IDENTITY CASCADE;
            """)

        self.stdout.write(self.style.WARNING(
            "🧹 Old data cleared and IDs reset."))

        # 🔹 Create service categories
        categories = ["Garage/Basement", "Lawncare", "House Cleaning"]
        category_objs = {
            name: ServiceCategory.objects.create(name=name) for name in categories
        }
        self.stdout.write(self.style.SUCCESS("✅ Service categories created."))

        # 🔹 Create standard time slots
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
        self.stdout.write(self.style.SUCCESS(
            "✅ Employees seeded with Dallas-area home addresses."))

        # 🔹 Seed bookings for next 28 days
        today = timezone.now().date()
        for day in range(28):
            booking_date = today + timedelta(days=day)

            for category_name, category_obj in category_objs.items():
                for slot_label, slot_obj in slot_objs.items():
                    if random.random() < 0.4:  # 40% chance slot has a booking
                        booking = Booking.objects.create(
                            customer_name=fake.name(),
                            customer_address=random.choice(DALLAS_ADDRESSES),
                            service_category=category_obj,
                            date=booking_date,
                            time_slot=slot_obj,
                        )

                        # Assign 1–3 employees from that category
                        available_emps = Employee.objects.filter(
                            service_category=category_obj)
                        for emp in random.sample(list(available_emps), random.randint(1, 3)):
                            JobAssignment.objects.create(
                                employee=emp,
                                booking=booking,
                                jobsite_address=booking.customer_address,
                            )

        self.stdout.write(self.style.SUCCESS(
            "✅ Bookings + assignments seeded for next 28 days with Dallas addresses."))
