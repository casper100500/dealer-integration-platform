from django.db import models


class Dealer(models.Model):
    name = models.CharField(max_length=255)
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
    )
    website_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return self.name


MAKE_CHOICES = [
    ("skoda", "Skoda"),
    ("toyota", "Toyota"),
    ("ford", "Ford"),
    ("honda", "Honda"),
    ("hyundai", "Hyundai"),
    ("kia", "Kia"),
    ("mazda", "Mazda"),
    ("mercedes_benz", "Mercedes-Benz"),
    ("nissan", "Nissan"),
    ("volkswagen", "Volkswagen"),
    ("other", "Other"),
]

BODY_STYLE_CHOICES = [
    ("sedan", "Sedan"),
    ("hatchback", "Hatchback"),
    ("wagon", "Wagon"),
    ("suv", "SUV"),
    ("coupe", "Coupe"),
    ("convertible", "Convertible"),
    ("pickup", "Pickup"),
    ("van", "Van"),
    ("other", "Other"),
]

FUEL_TYPE_CHOICES = [
    ("gasoline", "Gasoline"),
    ("diesel", "Diesel"),
    ("hybrid", "Hybrid"),
    ("plug_in_hybrid", "Plug-in hybrid"),
    ("electric", "Electric"),
    ("lpg", "LPG"),
    ("other", "Other"),
]

TRANSMISSION_CHOICES = [
    ("manual", "Manual"),
    ("automatic", "Automatic"),
    ("cvt", "CVT"),
    ("dual_clutch", "Dual-clutch"),
    ("other", "Other"),
]


class Vehicle(models.Model):
    vin = models.CharField(
        max_length=17,
        unique=True,
    )
    plate_number = models.CharField(max_length=20, blank=True)
    year = models.PositiveSmallIntegerField(blank=True, null=True)
    make = models.CharField(
        max_length=100,
        choices=MAKE_CHOICES,
        blank=True,
    )
    model = models.CharField(max_length=100, blank=True)
    exterior_color = models.CharField(max_length=100, blank=True)
    body_style = models.CharField(
        max_length=100,
        choices=BODY_STYLE_CHOICES,
        blank=True,
    )
    fuel_type = models.CharField(
        max_length=100,
        choices=FUEL_TYPE_CHOICES,
        blank=True,
    )
    engine = models.CharField(max_length=255, blank=True)
    transmission = models.CharField(
        max_length=100,
        choices=TRANSMISSION_CHOICES,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["make", "model", "year"]),
        ]

    def __str__(self) -> str:
        if self.vin:
            return self.vin

        description = " ".join(
            str(part) for part in [self.year, self.make, self.model] if part
        )
        return description or f"Vehicle {self.pk}"
