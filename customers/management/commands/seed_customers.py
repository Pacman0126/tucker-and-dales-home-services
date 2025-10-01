import random
import uuid
from django.core.management.base import BaseCommand
from faker import Faker
from customers.models import RegisteredCustomer

fake = Faker()

# 🔹 Dallas–Metroplex cities for realism
CITIES = [
    ("Dallas", "TX", "75201"),
    ("Plano", "TX", "75093"),
    ("Garland", "TX", "75040"),
    ("Irving", "TX", "75039"),
    ("Arlington", "TX", "76010"),
    ("Denton", "TX", "76201"),
    ("Carrollton", "TX", "75006"),
    ("Frisco", "TX", "75034"),
    ("Flower Mound", "TX", "75028"),
    ("Richardson", "TX", "75080"),
]


class Command(BaseCommand):
    help = "Seed 180 RegisteredCustomers in Dallas Metroplex"

    def handle(self, *args, **kwargs):
        # Clear existing customers
        RegisteredCustomer.objects.all().delete()
        self.stdout.write(self.style.WARNING(
            "🧹 Old RegisteredCustomers cleared."))

        # Seed 180 customers
        for _ in range(180):
            city, state, zipcode = random.choice(CITIES)
            RegisteredCustomer.objects.create(
                unique_customer_id=str(uuid.uuid4()),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                street_address=fake.street_address(),
                city=city,
                state=state,
                zipcode=zipcode,
                phone=fake.phone_number(),
                email=fake.unique.email(),
            )

        self.stdout.write(self.style.SUCCESS(
            "✅ 180 RegisteredCustomers created in Dallas Metroplex."))
