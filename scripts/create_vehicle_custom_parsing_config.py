from dealer_platform.dataimport.models import (
    VehicleDataImportParsingConfig,
    VehicleDataImportParsingConfigField,
)

CONFIG_NAME = "Config for custom fields"

FIELD_MAPPINGS = {
    "VIN Code": "vin",
    "License Plate": "plate_number",
    "Production Year": "year",
    "Manufacturer": "make",
    "Model Name": "model",
    "Paint Color": "exterior_color",
    "Vehicle Type": "body_style",
    "Fuel": "fuel_type",
    "Motor": "engine",
    "Transmission Type": "transmission",
}

COLUMNS_TO_SKIP = [
    "Stock Number",
    "Current Price",
    "Currency",
    "Mileage",
    "Dealer Notes",
    "Photo URL",
]

config, created = VehicleDataImportParsingConfig.objects.update_or_create(
    name=CONFIG_NAME,
    defaults={"columns_to_skip": COLUMNS_TO_SKIP},
)

config.fields.exclude(custom_field__in=FIELD_MAPPINGS.keys()).delete()

created_count = 0
updated_count = 0

for custom_field, object_field in FIELD_MAPPINGS.items():
    _, field_created = (
        VehicleDataImportParsingConfigField.objects.update_or_create(
            config=config,
            object_field=object_field,
            defaults={"custom_field": custom_field},
        )
    )

    if field_created:
        created_count += 1
    else:
        updated_count += 1

action = "Created" if created else "Updated"
print(
    f"{action} parsing config '{config.name}': "
    f"{created_count} fields created, {updated_count} fields updated, "
    f"{len(COLUMNS_TO_SKIP)} columns skipped."
)
