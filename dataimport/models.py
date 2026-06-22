from __future__ import annotations

from typing import Any

from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver


class ImportSource(models.TextChoices):
    django = ("django", "Django")
    usacar = ("usacar", "USAcar")


class ImportStatus(models.TextChoices):
    new = ("new", "New")
    in_progress = ("in_progress", "In progress")
    failed = ("failed", "Failed")
    done = ("done", "Done")


IMPORT_SOURCE_CHOICES = ImportSource.choices
IMPORT_STATUS_CHOICES = ImportStatus.choices
VEHICLE_OBJECT_FIELD_CHOICES = [
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
]


class VehicleDataImportParsingConfig(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Vehicle data import parsing config"
        verbose_name_plural = "Vehicle data import parsing configs"

    def __str__(self) -> str:
        return self.name


class VehicleDataImportParsingConfigField(models.Model):
    config = models.ForeignKey(
        VehicleDataImportParsingConfig,
        related_name="fields",
        on_delete=models.CASCADE,
    )
    object_field = models.CharField(
        max_length=50,
        choices=VEHICLE_OBJECT_FIELD_CHOICES,
    )
    custom_field = models.CharField(max_length=255)

    class Meta:
        unique_together = [["config", "object_field"]]
        verbose_name = "Vehicle data import parsing config field"
        verbose_name_plural = "Vehicle data import parsing config fields"

    def __str__(self) -> str:
        return f"{self.get_object_field_display()} <- {self.custom_field}"


class VehicaleDataImport(models.Model):
    dealer = models.ForeignKey(
        "inventory.Dealer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="data_imports",
    )
    source = models.CharField(max_length=50, choices=IMPORT_SOURCE_CHOICES)
    status = models.CharField(
        max_length=50,
        choices=IMPORT_STATUS_CHOICES,
        default=ImportStatus.new,
    )
    skipped = models.BooleanField(default=False)
    file = models.ForeignKey(
        "Files.File",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    parsing_config = models.ForeignKey(
        VehicleDataImportParsingConfig,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="data_imports",
    )
    records_total = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    records_skipped = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def parsed(self) -> str:
        if self.records_total == 0:
            if self.status == ImportStatus.done:
                return "100%"
            return "0%"

        imported = (
            self.records_created + self.records_updated + self.records_skipped
        )
        percent = min(round((imported / self.records_total) * 100), 100)
        return f"{percent}%"

    def __str__(self) -> str:
        return f"{self.get_source_display()} import #{self.pk}"


class AbstractImportMessage(models.Model):
    message = models.TextField()
    row_number = models.PositiveIntegerField(null=True, blank=True)
    raw_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.message


class VehicaleDataImportError(AbstractImportMessage):
    data_import = models.ForeignKey(
        VehicaleDataImport,
        related_name="errors",
        on_delete=models.CASCADE,
    )


class VehicaleDataImportWarning(AbstractImportMessage):
    data_import = models.ForeignKey(
        VehicaleDataImport,
        related_name="warnings",
        on_delete=models.CASCADE,
    )


@receiver(post_save, sender=VehicaleDataImport)
def run_vehicle_data_import(
    sender: type[VehicaleDataImport],
    instance: VehicaleDataImport,
    created: bool,
    **kwargs: Any,
) -> None:
    """Start a new vehicle data import after it is created."""
    if created and instance.status == ImportStatus.new:
        from .tasks import task_run_vehicle_data_import

        transaction.on_commit(
            lambda: task_run_vehicle_data_import.delay(instance.pk)
        )
