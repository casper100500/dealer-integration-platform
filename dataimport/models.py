from enum import Enum

from django.db import models


class ImportSource(Enum):
    django = ("django", "Django")
    usacar = ("usacar", "USAcar")


class ImportStatus(Enum):
    new = ("new", "New")
    in_progress = ("in_progress", "In progress")
    failed = ("failed", "Failed")
    done = ("done", "Done")


IMPORT_SOURCE_CHOICES = [item.value for item in ImportSource]
IMPORT_STATUS_CHOICES = [item.value for item in ImportStatus]


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
        default=ImportStatus.new.value[0],
    )
    skipped = models.BooleanField(default=False)
    file = models.ForeignKey(
        "Files.File",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
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
            if self.status == ImportStatus.done.value[0]:
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
