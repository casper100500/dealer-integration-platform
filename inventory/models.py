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


class Vehicle(models.Model):
    vin = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        unique=True,
    )
    year = models.PositiveSmallIntegerField(blank=True, null=True)
    make = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    trim = models.CharField(max_length=100, blank=True)
    body_style = models.CharField(max_length=100, blank=True)
    engine = models.CharField(max_length=255, blank=True)
    transmission = models.CharField(max_length=255, blank=True)
    drivetrain = models.CharField(max_length=100, blank=True)
    fuel_type = models.CharField(max_length=100, blank=True)
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
