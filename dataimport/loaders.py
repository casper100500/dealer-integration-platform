from __future__ import annotations

import csv
from contextlib import contextmanager
from typing import Any, Iterator, TextIO, TypedDict

from django.utils import timezone

from .models import ImportStatus, VehicaleDataImport

PARSED_SAVE_INTERVAL = 100

CsvRow = dict[str, str | None]
FieldMapping = dict[str, str]


class ImportCounters(TypedDict):
    total: int
    created: int
    updated: int
    skipped: int


class AbstractBaseLoader:
    """Run import lifecycle bookkeeping around a concrete import loader."""

    error_model: Any = None
    warning_model: Any = None
    import_name = "Data"

    def __init__(self, data_import: VehicaleDataImport) -> None:
        self.data_import = data_import

    def run(self) -> None:
        """Execute loading and persist lifecycle state."""
        self.data_import.status = ImportStatus.in_progress
        self.data_import.started_at = timezone.now()
        self.data_import.save(
            update_fields=["status", "started_at", "updated_at"]
        )

        try:
            self._load()
        except Exception as error:
            self.create_import_error(str(error))
            self.data_import.status = ImportStatus.failed
        else:
            if self.data_import.status == ImportStatus.in_progress:
                self.data_import.status = ImportStatus.done
        finally:
            self.data_import.finished_at = timezone.now()
            self.data_import.save(
                update_fields=[
                    "status",
                    "skipped",
                    "records_total",
                    "records_created",
                    "records_updated",
                    "records_skipped",
                    "started_at",
                    "finished_at",
                    "updated_at",
                ]
            )

    def _load(self) -> None:
        """Handle imports without an implemented loader."""
        self.data_import.skipped = True
        self.data_import.status = ImportStatus.done
        self.create_warning(
            f"{self.import_name} loader for source "
            f"{self.data_import.get_source_display()} is not implemented."
        )

    def create_import_error(self, message: str) -> None:
        """Persist an import-level error message."""
        self.error_model.objects.create(
            data_import=self.data_import,
            message=message,
        )

    def create_warning(self, message: str) -> None:
        """Persist an import-level warning message."""
        self.warning_model.objects.create(
            data_import=self.data_import,
            message=message,
        )


class CsvBaseLoader(AbstractBaseLoader):
    """Read CSV rows, update counters, and delegate row-specific work."""

    def _load(self) -> None:
        counters: ImportCounters = {
            "total": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
        }

        field_mapping = self.get_field_mapping()

        with self.open_csv() as csvfile:
            reader = csv.DictReader(csvfile)
            counters["total"] = sum(1 for _ in reader)
            self.save_parsed(counters)

            csvfile.seek(0)
            reader = csv.DictReader(csvfile)

            for line_number, row in enumerate(reader, start=2):
                raw_row = dict(row)
                row_data = self.normalize_row(raw_row, field_mapping)

                try:
                    errors = self.validate_row(row_data)
                    if errors:
                        counters["skipped"] += 1
                        for error in errors:
                            self.create_row_error(
                                line_number,
                                raw_row,
                                error,
                            )
                    else:
                        if self.save_row(row_data):
                            counters["created"] += 1
                        else:
                            counters["updated"] += 1
                except Exception as error:
                    counters["skipped"] += 1
                    self.create_row_error(line_number, raw_row, str(error))

                if self.processed_count(counters) % PARSED_SAVE_INTERVAL == 0:
                    self.save_parsed(counters)

        self.save_parsed(counters)

    @contextmanager
    def open_csv(self) -> Iterator[TextIO]:
        """Open the import CSV file with BOM-safe UTF-8 decoding."""
        if not self.data_import.file:
            raise ValueError(
                f"{self.import_name.lower()} import file is required"
            )

        with open(
            self.data_import.file.file.path,
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as csvfile:
            yield csvfile

    def get_field_mapping(self) -> FieldMapping | None:
        """Return optional source field to object field mapping."""
        return None

    def normalize_row(
        self,
        row: CsvRow,
        field_mapping: FieldMapping | None,
    ) -> CsvRow:
        """Convert a raw CSV row into row data expected by save_row."""
        return row

    def validate_row(self, row: CsvRow) -> list[str]:
        """Return row validation errors before saving."""
        return []

    def save_row(self, row: CsvRow) -> bool:
        """Persist a normalized row and return whether it was created."""
        raise NotImplementedError

    def processed_count(self, counters: ImportCounters) -> int:
        """Return the number of rows already handled."""
        return counters["created"] + counters["updated"] + counters["skipped"]

    def save_parsed(self, counters: ImportCounters) -> None:
        """Persist current import counters to the data import record."""
        self.data_import.records_total = counters["total"]
        self.data_import.records_created = counters["created"]
        self.data_import.records_updated = counters["updated"]
        self.data_import.records_skipped = counters["skipped"]
        self.data_import.save(
            update_fields=[
                "records_total",
                "records_created",
                "records_updated",
                "records_skipped",
                "updated_at",
            ]
        )

    def create_row_error(
        self,
        line_number: int,
        row: CsvRow,
        message: str,
    ) -> None:
        """Persist a row-level validation or processing error."""
        self.error_model.objects.create(
            data_import=self.data_import,
            row_number=line_number,
            raw_data=row,
            message=f"line {line_number} {message}",
        )
