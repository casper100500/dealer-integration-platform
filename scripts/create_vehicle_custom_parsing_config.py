from dealer_platform.dataimport.models import (
    VehicleDataImportColumn,
    VehicleDataImportParsingConfig,
    VehicleDataImportParsingConfigField,
)

CONFIG_NAME = "Config for custom fields"

FIELD_MAPPINGS = {
    "VIN Code": VehicleDataImportColumn.vin,
    "License Plate": VehicleDataImportColumn.plate_number,
    "Production Year": VehicleDataImportColumn.year,
    "Manufacturer": VehicleDataImportColumn.make,
    "Model Name": VehicleDataImportColumn.model,
    "Paint Color": VehicleDataImportColumn.exterior_color,
    "Vehicle Type": VehicleDataImportColumn.body_style,
    "Fuel": VehicleDataImportColumn.fuel_type,
    "Motor": VehicleDataImportColumn.engine,
    "Transmission Type": VehicleDataImportColumn.transmission,
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
