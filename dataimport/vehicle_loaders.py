from __future__ import annotations

from typing import Any, cast

from django.db import models

from inventory.models import Vehicle

from .loaders import CsvBaseLoader, CsvRow, FieldMapping
from .models import (
    VehicaleDataImportError,
    VehicaleDataImportWarning,
)


class VehicleBaseLoader(CsvBaseLoader):
    """Parse CSV rows into standard Vehicle fields and persist vehicles."""

    error_model = VehicaleDataImportError
    warning_model = VehicaleDataImportWarning
    import_name = "Vehicle"
    standard_mapping: FieldMapping = {
        "vin": "vin",
        "plate_number": "plate_number",
        "year": "year",
        "make": "make",
        "model": "model",
        "exterior_color": "exterior_color",
        "body_style": "body_style",
        "fuel_type": "fuel_type",
        "engine": "engine",
        "transmission": "transmission",
    }

    def get_field_mapping(self) -> FieldMapping:
        """Use parsing config mapping, or standard field names by default."""
        if not self.data_import.parsing_config_id:
            return self.standard_mapping

        parsing_config = self.data_import.parsing_config
        if parsing_config is None:
            return self.standard_mapping

        return {
            field.custom_field: field.object_field
            for field in parsing_config.fields.all()
        }

    def normalize_row(
        self,
        row: CsvRow,
        field_mapping: FieldMapping | None,
    ) -> CsvRow:
        """Map source CSV fields onto supported Vehicle model fields."""
        if field_mapping is None:
            field_mapping = self.standard_mapping

        row = self.skip_columns(row)

        return {
            object_field: row.get(source_field)
            for source_field, object_field in field_mapping.items()
            if object_field in self.standard_mapping.values()
        }

    def skip_columns(self, row: CsvRow) -> CsvRow:
        """Remove source columns configured to be ignored."""
        parsing_config = self.data_import.parsing_config
        if parsing_config is None:
            return row

        return {
            field_name: value
            for field_name, value in row.items()
            if field_name not in parsing_config.columns_to_skip
        }

    def validate_row(self, row: CsvRow) -> list[str]:
        """Validate required vehicle identity and basic field types/lengths."""
        errors: list[str] = []

        if not row.get("vin"):
            errors.append("the VIN is required")

        for field_name in set(self.standard_mapping.values()) - {"year"}:
            field = cast(
                "models.Field[Any, Any]",
                Vehicle._meta.get_field(field_name),
            )
            value = row.get(field_name) or ""
            if field.max_length and len(value) > field.max_length:
                errors.append(f"the {field.verbose_name} is too long")

        year = row.get("year")
        if year and not self.is_integer(year):
            errors.append("the year is not a valid integer")

        return errors

    def save_row(self, row: CsvRow) -> bool:
        """Create or update a Vehicle from a normalized row."""
        vin = row.get("vin")
        if vin is None:
            raise ValueError("the VIN is required")

        _, created = Vehicle.objects.update_or_create(
            vin=vin,
            defaults=self.build_vehicle_defaults(row),
        )
        return created

    def build_vehicle_defaults(self, row: CsvRow) -> dict[str, Any]:
        """Build Vehicle defaults for update_or_create."""
        return {
            "vin": row.get("vin") or "",
            "plate_number": row.get("plate_number") or "",
            "year": self.to_integer(row.get("year")),
            "make": row.get("make") or "",
            "model": row.get("model") or "",
            "exterior_color": row.get("exterior_color") or "",
            "body_style": row.get("body_style") or "",
            "fuel_type": row.get("fuel_type") or "",
            "engine": row.get("engine") or "",
            "transmission": row.get("transmission") or "",
        }

    def is_integer(self, value: str) -> bool:
        """Return whether a CSV value can be converted to an integer."""
        try:
            int(value)
        except ValueError:
            return False
        return True

    def to_integer(self, value: str | None) -> int | None:
        """Convert an optional CSV value to an integer."""
        if value is None or value == "":
            return None
        return int(value)


class VehicleDjangoLoader(VehicleBaseLoader):
    """Default Django-admin vehicle CSV import loader."""

    pass
