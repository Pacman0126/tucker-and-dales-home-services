import random
import logging
import uuid
from django.core.management.base import BaseCommand
from faker import Faker
from customers.models import RegisteredCustomer

logger = logging.getLogger("django")

DALLAS_STREETS = [
    "Main St", "Elm St", "Commerce St", "Cedar Springs Rd", "Ross Ave",
    "McKinney Ave", "Lamar St", "Maple Ave", "Lovers Ln", "Mockingbird Ln",
    "Abrams Rd", "Royal Ln", "Northwest Hwy", "Skillman St", "Greenville Ave",
    "Forest Ln", "Coit Rd", "Campbell Rd", "Spring Valley Rd", "Preston Rd",
    "Inwood Rd", "Walnut Hill Ln", "Park Ln", "Hillcrest Rd", "Montfort Dr"
]


class Command(BaseCommand):
    help = "Seed the database with at least 180 fake Dallas customers"

    def handle(self, *args, **kwargs):
        fake = Faker()
        Faker.seed(42)

        # Wipe old data first
        RegisteredCustomer.objects.all().delete()
        logger.info("Deleted old RegisteredCustomer records.")

        customers = []
        while len(customers) < 200:  # generate 200 candidates
            street = random.choice(DALLAS_STREETS)
            house_number = random.randint(100, 9999)
            address = f"{house_number} {street}"

            customers.append(RegisteredCustomer(
                unique_customer_id=str(uuid.uuid4()),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                street_address=address,
                city="Dallas",
                state="TX",
                zipcode=fake.zipcode_in_state(state_abbr="TX"),
                phone=fake.phone_number(),
                email=fake.unique.email(),  # must be unique
            ))

        # Insert exactly 180
        RegisteredCustomer.objects.bulk_create(customers[:180])

        self.stdout.write(self.style.SUCCESS(
            "Seeded 180 customers into the database."))
