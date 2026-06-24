# Generated manually after adding imported vehicle price data.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dataimport", "0005_require_vehicaledataimport_dealer"),
    ]

    operations = [
        migrations.AlterField(
            model_name="vehicledataimportparsingconfigfield",
            name="object_field",
            field=models.CharField(
                choices=[
                    ("vin", "VIN"),
                    ("plate_number", "Plate number"),
                    ("year", "Year"),
                    ("make", "Make"),
                    ("model", "Model"),
                    ("exterior_color", "Exterior color"),
                    ("body_style", "Body style"),
                    ("fuel_type", "Fuel type"),
                    ("engine", "Engine"),
                    ("transmission", "Transmission"),
                    ("price", "Price"),
                    ("currency", "Currency"),
                ],
                max_length=50,
            ),
        ),
    ]
