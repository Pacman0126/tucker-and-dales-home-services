from django.core.management.base import BaseCommand
from faker import Faker
import random
from datetime import timedelta, date
from scheduling.models import ServiceCategory, Employee, Booking, JobAssignment, TimeSlot

fake = Faker()


class Command(BaseCommand):
    help = "Seed database with employees, categories, time slots, and sample bookings"

    def handle(self, *args, **kwargs):
        # 1. Service categories
        categories = ["Garage/Basement", "Lawncare", "House Cleaning"]
        category_objs = {
            name: ServiceCategory.objects.get_or_create(name=name)[0]
            for name in categories
        }

        # 2. Time slots
        slot_labels = ["7:30-9:30", "10:00-12:00", "12:30-2:30", "3:00-5:00"]
        slot_objs = {
            label: TimeSlot.objects.get_or_create(label=label)[0] for label in slot_labels
        }

        # 3. Employees (5 per category)
        for category in category_objs.values():
            for _ in range(5):
                Employee.objects.get_or_create(
                    name=fake.name(),
                    home_address=fake.address(),
                    service_category=category,
                )

        self.stdout.write(self.style.SUCCESS(
            "✅ Service categories, slots, and employees created."))

        # 4. Seed bookings over next 7 days
        employees = list(Employee.objects.all())
        today = date.today()

        for d in (today + timedelta(days=i) for i in range(7)):
            for category in category_objs.values():
                for slot in slot_objs.values():
                    if random.random() < 0.5:  # ~50% chance a slot has a booking
                        booking = Booking.objects.create(
                            customer_name=fake.name(),
                            customer_address=fake.address(),
                            date=d,
                            time_slot=slot,
                            service_category=category,
                        )

                        # Assign 1–3 employees to this booking
                        assigned = random.sample(
                            [e for e in employees if e.service_category == category],
                            k=random.randint(1, 3),
                        )
                        for emp in assigned:
                            JobAssignment.objects.create(
                                employee=emp, booking=booking, jobsite_address=booking.customer_address
                            )

        self.stdout.write(self.style.SUCCESS(
            "✅ Sample bookings and job assignments created."))
