from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),  # adjust accordingly
    ]

    operations = [
        migrations.AddField(
            model_name="paymenthistory",
            name="adjustments_total_amt",
            field=models.DecimalField(
                max_digits=10, decimal_places=2, default=Decimal("0.00")
            ),
            preserve_default=False,
        ),
    ]
