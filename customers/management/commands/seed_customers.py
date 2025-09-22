import uuid
import random
from faker import Faker
from django.core.management.base import BaseCommand
from customers.models import RegisteredCustomer

fake = Faker("en_US")

CITIES = [
    "Dallas", "Fort Worth", "Arlington", "Plano", "Irving", "Garland",
    "Grand Prairie", "McKinney", "Frisco", "Mesquite", "Carrollton",
    "Richardson", "Lewisville", "Allen", "Flower Mound", "Denton",
    "North Richland Hills", "Cedar Hill", "Grapevine", "Mansfield"
]

TARGET_COUNT = 180


class Command(BaseCommand):
    help = "Seed the database with unique RegisteredCustomer records."

    def handle(self, *args, **options):
        RegisteredCustomer.objects.all().delete()
        self.stdout.write(self.style.WARNING(
            "Deleted old RegisteredCustomer records."))

        used_names = set()
        created = 0

        while created < TARGET_COUNT:
            first = fake.first_name()
            last = fake.last_name()

            if (first, last) in used_names:
                continue
            used_names.add((first, last))

            street_address = f"{random.randint(100, 9999)} {fake.street_name()}"
            city = random.choice(CITIES)
            state = "TX"
            zipcode = fake.zipcode_in_state(state_abbr="TX")
            phone = fake.numerify("###-###-####")
            email = f"{first.lower()}.{last.lower()}{random.randint(1, 9999)}@example.com"

            RegisteredCustomer.objects.create(
                unique_customer_id=str(uuid.uuid4()),
                first_name=first,
                last_name=last,
                street_address=street_address,
                city=city,
                state=state,
                zipcode=zipcode,
                phone=phone,
                email=email,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created} unique customers."))
