from dealer_platform.inventory.models import Dealer

DEALERS = [
    {
        "external_id": "northside-motors",
        "name": "Northside Motors",
        "website_url": "https://northside-motors.example.com",
        "is_active": True,
    },
    {
        "external_id": "lakeside-autos",
        "name": "Lakeside Autos",
        "website_url": "https://lakeside-autos.example.com",
        "is_active": True,
    },
    {
        "external_id": "downtown-cars",
        "name": "Downtown Cars",
        "website_url": "https://downtown-cars.example.com",
        "is_active": True,
    },
    {
        "external_id": "usa-car",
        "name": "USA Car",
        "website_url": "https://usa-car.example.com",
        "is_active": True,
    },
]


created_count = 0
updated_count = 0

for dealer_data in DEALERS:
    dealer, created = Dealer.objects.update_or_create(
        external_id=dealer_data["external_id"],
        defaults=dealer_data,
    )

    if created:
        created_count += 1
    else:
        updated_count += 1

print(
    f"Seeded dealers: {created_count} created, "
    f"{updated_count} updated, {Dealer.objects.count()} total."
)
