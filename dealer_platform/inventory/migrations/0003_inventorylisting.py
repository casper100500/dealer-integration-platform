# Generated manually after adding dealer-specific inventory listings.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "inventory",
            "0002_remove_vehicle_drivetrain_remove_vehicle_trim_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryListing",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        blank=True,
                        choices=[("USD", "USD"), ("EUR", "EUR")],
                        max_length=3,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="inventory_listings",
                        to="inventory.dealer",
                    ),
                ),
                (
                    "vehicle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inventory_listings",
                        to="inventory.vehicle",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="inventorylisting",
            constraint=models.UniqueConstraint(
                fields=("dealer", "vehicle"),
                name="unique_dealer_vehicle_listing",
            ),
        ),
        migrations.AddIndex(
            model_name="inventorylisting",
            index=models.Index(
                fields=["dealer", "vehicle"],
                name="inventory_i_dealer__fa5874_idx",
            ),
        ),
    ]
