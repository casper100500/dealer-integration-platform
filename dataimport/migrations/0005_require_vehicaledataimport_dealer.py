# Generated manually after clearing nullable vehicle data imports.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dataimport", "0004_vehicledataimportparsingconfig_columns_to_skip"),
        (
            "inventory",
            "0002_remove_vehicle_drivetrain_remove_vehicle_trim_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="vehicaledataimport",
            name="dealer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="data_imports",
                to="inventory.dealer",
            ),
        ),
    ]
