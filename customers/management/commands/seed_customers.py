from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker

from customers.models import CustomerProfile
from real_dfw_addresses import REAL_DFW_ADDRESSES

fake = Faker()

# ------------------------------------------------------------
# 🗺️ Service-Area Mapping by ZIP Prefix
# ------------------------------------------------------------
# Keep this logic because it reflects the Dallas-area operating zones
# of the demo business. We do NOT write these long labels into the
# current CustomerProfile.region field, because region is now used as
# a short country/locale code (e.g. "US").
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
    zipcode = (zipcode or "").strip()
    for region, prefixes in REGION_MAP.items():
        for prefix in prefixes:
            if zipcode.startswith(prefix):
                return region
    return "Other"


def parse_address(address: str) -> dict:
    """
    Parse addresses shaped like:
    '123 Main St, Dallas, TX 75201'
    """
    parts = [p.strip() for p in address.split(",")]

    street = parts[0] if len(parts) > 0 else ""
    city = parts[1] if len(parts) > 1 else ""
    state_zip = parts[2] if len(parts) > 2 else ""

    state = ""
    zipcode = ""

    if state_zip:
        tokens = state_zip.split()
        if len(tokens) >= 1:
            state = tokens[0]
        if len(tokens) >= 2:
            zipcode = tokens[1]

    return {
        "street": street,
        "city": city,
        "state": state,
        "zipcode": zipcode,
    }


class Command(BaseCommand):
    help = (
        "Restore/backfill CustomerProfile rows for existing preserved non-superuser demo users "
        "using real_dfw_addresses.py. This command does NOT recreate users."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=len(REAL_DFW_ADDRESSES),
            help="How many preserved non-superuser users to backfill. Defaults to the number of real DFW addresses.",
        )
        parser.add_argument(
            "--purge-extra-users",
            action="store_true",
            help="Delete non-superuser users beyond the selected preserved pool after dry-run is verified.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without writing changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        purge_extra_users = options["purge_extra_users"]
        requested_limit = options["limit"]

        address_count = len(REAL_DFW_ADDRESSES)
        if requested_limit < 1:
            raise ValueError("--limit must be at least 1.")

        preserve_limit = min(requested_limit, address_count)

        all_non_superusers = list(
            User.objects.filter(is_superuser=False).order_by("id")
        )

        total_non_superusers = len(all_non_superusers)
        if total_non_superusers == 0:
            self.stdout.write(self.style.WARNING(
                "No non-superuser users found."))
            return

        preserved_users = all_non_superusers[:preserve_limit]
        extra_users = all_non_superusers[preserve_limit:]

        self.stdout.write(
            self.style.NOTICE(
                f"Non-superusers found: {total_non_superusers} | "
                f"Preserved for profile restore: {len(preserved_users)} | "
                f"Extra users beyond limit: {len(extra_users)} | "
                f"Address pool size: {address_count}"
            )
        )

        # Preview the first few preserved users
        preview_count = min(10, len(preserved_users))
        if preview_count:
            self.stdout.write("First preserved users by id order:")
            for user in preserved_users[:preview_count]:
                self.stdout.write(
                    f"  id={user.id} | username={user.username} | email={user.email}"
                )

        if purge_extra_users and extra_users:
            self.stdout.write(
                self.style.WARNING(
                    f"{'Would delete' if dry_run else 'Deleting'} {len(extra_users)} extra non-superuser account(s) beyond the preserved pool..."
                )
            )
            if not dry_run:
                User.objects.filter(
                    id__in=[u.id for u in extra_users]).delete()

        # Refresh preserved users after optional purge
        preserved_ids = [u.id for u in preserved_users]
        preserved_users = list(
            User.objects.filter(id__in=preserved_ids).order_by("id")
        )

        # Remove existing profiles only for the preserved cohort,
        # then recreate them cleanly from the fixed address list.
        existing_profiles = CustomerProfile.objects.filter(
            user__in=preserved_users)
        existing_profile_count = existing_profiles.count()

        self.stdout.write(
            self.style.WARNING(
                f"{'Would remove' if dry_run else 'Removing'} {existing_profile_count} existing profile(s) "
                f"for preserved users..."
            )
        )
        if not dry_run and existing_profile_count:
            existing_profiles.delete()

        created_count = 0

        for index, user in enumerate(preserved_users):
            raw_address = REAL_DFW_ADDRESSES[index]
            parsed = parse_address(raw_address)
            service_area = infer_region(parsed["zipcode"])

            email_value = (user.email or "").strip()
            if not email_value:
                email_value = f"{user.username}@example.com"

            profile_kwargs = {
                "user": user,
                "email": email_value,
                "phone": fake.phone_number()[:20],
                "company": "",
                "preferred_contact": "email",
                "timezone": "America/Chicago",

                # Billing snapshot
                "billing_street_address": parsed["street"],
                "billing_city": parsed["city"],
                "billing_state": parsed["state"],
                "billing_zipcode": parsed["zipcode"],

                # Current model meaning: short country/locale code
                "region": "US",

                # Service snapshot
                "service_street_address": parsed["street"],
                "service_city": parsed["city"],
                "service_state": parsed["state"],
                "service_zipcode": parsed["zipcode"],
                "service_region": "US",
            }

            if dry_run:
                created_count += 1
                if created_count <= 10:
                    self.stdout.write(
                        f"[DRY RUN] Would restore profile for {user.username} | "
                        f"{parsed['street']}, {parsed['city']}, {parsed['state']} {parsed['zipcode']} | "
                        f"service_area={service_area}"
                    )
                continue

            CustomerProfile.objects.create(**profile_kwargs)
            created_count += 1

            if created_count <= 10:
                self.stdout.write(
                    f"✅ Restored {user.username} | "
                    f"{parsed['street']}, {parsed['city']}, {parsed['state']} {parsed['zipcode']} | "
                    f"service_area={service_area}"
                )
            elif created_count % 25 == 0:
                self.stdout.write(
                    f"✅ Restored {created_count} customer profiles...")

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would restore' if dry_run else 'Restored'} {created_count} CustomerProfile row(s) "
                f"for preserved users."
            )
        )

        if extra_users and not purge_extra_users:
            self.stdout.write(
                self.style.WARNING(
                    f"Note: {len(extra_users)} extra non-superuser account(s) were left untouched because "
                    f"--purge-extra-users was not used."
                )
            )
