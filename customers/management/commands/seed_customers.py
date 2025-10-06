import time
import random
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from faker import Faker
from customers.models import RegisteredCustomer
# 👈 your curated 180-address list
from real_dfw_addresses import REAL_DFW_ADDRESSES

fake = Faker()


def geocode_address(address):
    """
    Calls Google Geocoding API (server key) to validate and normalize an address.
    Returns formatted address dict or None if lookup fails.
    """
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
                "street_address": street_address,
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


class Command(BaseCommand):
    help = "Seeds 180 realistic RegisteredCustomers using verified addresses from real_dfw_addresses.py"

    def handle(self, *args, **kwargs):
        RegisteredCustomer.objects.all().delete()
        self.stdout.write(self.style.WARNING(
            "🧹 Cleared old RegisteredCustomers."))

        total_seeded = 0
        failures = 0

        for address in REAL_DFW_ADDRESSES:
            geo = geocode_address(address)
            time.sleep(0.25)  # ~4 requests/sec safe limit for Google API

            if not geo:
                failures += 1
                continue

            RegisteredCustomer.objects.create(
                unique_customer_id=fake.uuid4(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                street_address=geo["street_address"],
                city=geo["city"],
                state=geo["state"],
                zipcode=geo["zipcode"],
                phone=fake.phone_number(),
                email=fake.unique.email(),
            )

            total_seeded += 1
            if total_seeded % 20 == 0:
                self.stdout.write(
                    f"✅ Seeded {total_seeded} verified customers...")

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 Successfully seeded {total_seeded} RegisteredCustomers "
                f"(with {failures} skipped geocode failures)."
            )
        )
