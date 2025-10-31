import time
import uuid
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.text import slugify
from faker import Faker
from customers.models import RegisteredCustomer
from real_dfw_addresses import REAL_DFW_ADDRESSES

# ------------------------------------------------------------
# 🗺️ Region Mapping by ZIP Prefix
# ------------------------------------------------------------
REGION_MAP = {
    "Dallas": ["752", "75001", "75006"],
    "Plano / Richardson / Allen / Garland": ["75024", "75025", "75081", "75082", "75040", "75044"],
    "Frisco / McKinney / The Colony": ["75033", "75034", "75035", "75070", "75056"],
    "Irving / Las Colinas / Coppell": ["75038", "75039", "75063", "75062"],
    "Carrollton / Lewisville / Flower Mound": ["75006", "75007", "75028", "75067"],
    "Fort Worth / Arlington / Grand Prairie": ["761", "760", "75052"],
    "Denton / North Suburbs": ["762"],
}


def infer_region(zipcode: str) -> str:
    for region, prefixes in REGION_MAP.items():
        for prefix in prefixes:
            if zipcode.startswith(prefix):
                return region
    return "Other"


fake = Faker()


# ------------------------------------------------------------
# 📍 Google Geocoding (optional)
# ------------------------------------------------------------
def geocode_address(address):
    """Validate and normalize a Dallas/Fort Worth address via Google API."""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": settings.GOOGLE_MAPS_SERVER_KEY}

    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("status") == "OK":
            result = data["results"][0]
            components = {c["types"][0]: c["long_name"]
                          for c in result["address_components"]}
            formatted = result["formatted_address"]

            street_address = formatted.split(",")[0]
            city = components.get("locality") or components.get(
                "sublocality") or "Dallas"
            state = components.get("administrative_area_level_1", "TX")
            zipcode = components.get("postal_code", "75000")

            return {
                "street": street_address,
                "city": city,
                "state": state,
                "zipcode": zipcode,
                "formatted": formatted,
            }
        else:
            print(f"⚠️ Geocode failed for '{address}': {data.get('status')}")
            return None
    except Exception as e:
        print(f"❌ Geocode error for '{address}': {e}")
        return None


# ------------------------------------------------------------
# 🎯 Django Command
# ------------------------------------------------------------
class Command(BaseCommand):
    help = "Seeds realistic RegisteredCustomers using real_dfw_addresses.py"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-geocode",
            action="store_true",
            help="Skip Google geocoding for faster seeding (uses dummy city/state/zip)",
        )

    def handle(self, *args, **options):
        skip_geo = options["skip_geocode"]

        # 🧹 Clean existing data (non-superusers only)
        RegisteredCustomer.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING(
            "🧹 Cleared old customers and users."))

        total_seeded = 0

        for address in REAL_DFW_ADDRESSES:
            # Optionally geocode or fake the geo data
            if skip_geo:
                geo = {
                    "street": address.split(",")[0],
                    "city": "Dallas",
                    "state": "TX",
                    "zipcode": "75001",
                }
            else:
                geo = geocode_address(address)
                time.sleep(0.25)  # avoid hitting API rate limits

            if not geo:
                continue

            first = fake.first_name()
            last = fake.last_name()

            base_username = slugify(f"{first}.{last}")[:25]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            email = f"{username}@example.com"

            # ✅ Create Django User
            user = User.objects.create_user(
                username=username,
                email=email,
                password="password123",
                first_name=first,
                last_name=last,
            )

            # ✅ Map ZIP → region
            region = infer_region(geo["zipcode"])

            # ✅ Create RegisteredCustomer (matching your new model)
            RegisteredCustomer.objects.create(
                user=user,
                unique_customer_id=uuid.uuid4(),
                first_name=first,
                last_name=last,
                email=email,
                phone=fake.phone_number(),
                billing_street_address=geo["street"],
                billing_city=geo["city"],
                billing_state=geo["state"],
                billing_zipcode=geo["zipcode"],
                region=region,
            )

            total_seeded += 1
            if total_seeded % 20 == 0:
                self.stdout.write(f"✅ Seeded {total_seeded} customers...")

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 Successfully seeded {total_seeded} RegisteredCustomers "
                f"(login with <username>/password123)"
            )
        )
