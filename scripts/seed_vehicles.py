from dealer_platform.inventory.models import Vehicle

VEHICLES = [
    {
        "vin": "TMBKK61Z3C2131743",
        "plate_number": "CA6247HT",
        "year": 2012,
        "make": "skoda",
        "model": "Octavia",
        "exterior_color": "Gray",
        "body_style": "wagon",
        "fuel_type": "gasoline",
        "engine": "Gasoline, 1.8 L",
        "transmission": "manual",
    },
    {
        "vin": "4T1BF1FK0HU000001",
        "plate_number": "CA7T0Y1",
        "year": 2017,
        "make": "toyota",
        "model": "Camry",
        "exterior_color": "White",
        "body_style": "sedan",
        "fuel_type": "gasoline",
        "engine": "Gasoline, 2.5 L",
        "transmission": "automatic",
    },
    {
        "vin": "1FTEW1EP0MFA00001",
        "plate_number": "TXF1501",
        "year": 2021,
        "make": "ford",
        "model": "F-150",
        "exterior_color": "Blue",
        "body_style": "pickup",
        "fuel_type": "gasoline",
        "engine": "Gasoline, 2.7 L EcoBoost",
        "transmission": "automatic",
    },
    {
        "vin": "2HKRW2H50LH000001",
        "plate_number": "NYCRV01",
        "year": 2020,
        "make": "honda",
        "model": "CR-V",
        "exterior_color": "Black",
        "body_style": "suv",
        "fuel_type": "gasoline",
        "engine": "Gasoline, 1.5 L Turbo",
        "transmission": "cvt",
    },
    {
        "vin": "W1KWF8DB0MR000001",
        "plate_number": "FLMB001",
        "year": 2021,
        "make": "mercedes_benz",
        "model": "C-Class",
        "exterior_color": "Silver",
        "body_style": "sedan",
        "fuel_type": "gasoline",
        "engine": "Gasoline, 2.0 L Turbo",
        "transmission": "automatic",
    },
]


created_count = 0
updated_count = 0

for vehicle_data in VEHICLES:
    vehicle, created = Vehicle.objects.update_or_create(
        vin=vehicle_data["vin"],
        defaults=vehicle_data,
    )

    if created:
        created_count += 1
    else:
        updated_count += 1

print(
    f"Seeded vehicles: {created_count} created, "
    f"{updated_count} updated, {Vehicle.objects.count()} total."
)
