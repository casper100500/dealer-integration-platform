from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("dataimport", "0006_add_price_currency_mapping_choices"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="VehicaleDataImport",
            new_name="VehicleDataImport",
        ),
        migrations.RenameModel(
            old_name="VehicaleDataImportError",
            new_name="VehicleDataImportError",
        ),
        migrations.RenameModel(
            old_name="VehicaleDataImportWarning",
            new_name="VehicleDataImportWarning",
        ),
    ]
