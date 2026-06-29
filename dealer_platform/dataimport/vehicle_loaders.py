from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, cast

from django.db import models

from dealer_platform.inventory.models import (
    CURRENCY_CHOICES,
    DealerOffer,
    Vehicle,
)

from .loaders import CsvBaseLoader, CsvRow, FieldMapping
from .models import (
    VehicleDataImportError,
    VehicleDataImportWarning,
)


class VehicleBaseLoader(CsvBaseLoader):
    """Parse CSV rows into standard Vehicle fields and persist vehicles."""

    error_model = VehicleDataImportError
    warning_model = VehicleDataImportWarning
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
        "price": "price",
        "currency": "currency",
    }
    vehicle_fields = {
        "vin",
        "plate_number",
        "year",
        "make",
        "model",
        "exterior_color",
        "body_style",
        "fuel_type",
        "engine",
        "transmission",
    }
    supported_currencies = {currency for currency, _ in CURRENCY_CHOICES}

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

        for field_name in self.vehicle_fields - {"year"}:
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

        price = row.get("price")
        if price and self.to_decimal(price) is None:
            errors.append("the price is not a valid decimal")

        currency = self.normalize_currency(row.get("currency"))
        if currency and currency not in self.supported_currencies:
            errors.append("the currency is not supported")

        return errors

    def save_row(self, row: CsvRow) -> bool:
        """Create or update a Vehicle from a normalized row."""
        vin = row.get("vin")
        if vin is None:
            raise ValueError("the VIN is required")

        vehicle, vehicle_created = Vehicle.objects.update_or_create(
            vin=vin,
            defaults=self.build_vehicle_defaults(row),
        )
        _, offer_created = DealerOffer.objects.update_or_create(
            dealer=self.data_import.dealer,
            vehicle=vehicle,
            defaults=self.build_offer_defaults(row),
        )
        return vehicle_created or offer_created

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

    def build_offer_defaults(self, row: CsvRow) -> dict[str, Any]:
        """Build dealer offer defaults for update_or_create."""
        return {
            "price": self.to_decimal(row.get("price")),
            "currency": self.normalize_currency(row.get("currency")),
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

    def to_decimal(self, value: str | None) -> Decimal | None:
        """Convert an optional CSV value to a decimal price."""
        if value is None or value.strip() == "":
            return None

        try:
            return Decimal(value.strip().replace(",", ""))
        except InvalidOperation:
            return None

    def normalize_currency(self, value: str | None) -> str:
        """Normalize optional currency codes for storage."""
        if value is None:
            return ""
        return value.strip().upper()


class VehicleDjangoLoader(VehicleBaseLoader):
    """Default Django-admin vehicle CSV import loader."""

    pass


class VehicleUSACarLoader(VehicleBaseLoader):
    """Parse provider-specific USA Car CSV imports."""

    standard_mapping: FieldMapping = {
        "vin_code": "vin",
        "registration": "plate_number",
        "model_year": "year",
        "manufacturer": "make",
        "model_name": "model",
        "paint": "exterior_color",
        "category": "body_style",
        "fuel": "fuel_type",
        "motor": "engine",
        "gearbox": "transmission",
        "amount_cents": "price",
        "currency_code": "currency",
    }
    make_mapping = {
        "FORD": "ford",
        "HONDA": "honda",
        "HYUNDAI": "hyundai",
        "KIA": "kia",
        "MAZDA": "mazda",
        "MERCEDES_BENZ": "mercedes_benz",
        "NISSAN": "nissan",
        "SKODA": "skoda",
        "TOYOTA": "toyota",
        "VOLKSWAGEN": "volkswagen",
    }
    body_style_mapping = {
        "CONVERTIBLE": "convertible",
        "COUPE": "coupe",
        "HATCHBACK": "hatchback",
        "MINIVAN": "van",
        "PICKUP_TRUCK": "pickup",
        "SEDAN": "sedan",
        "SPORT_UTILITY": "suv",
        "VAN": "van",
        "WAGON": "wagon",
    }
    fuel_type_mapping = {
        "DIESEL": "diesel",
        "ELECTRIC": "electric",
        "GAS": "gasoline",
        "HYBRID": "hybrid",
        "LPG": "lpg",
        "PLUG_IN_HYBRID": "plug_in_hybrid",
    }
    transmission_mapping = {
        "AUTO": "automatic",
        "CVT": "cvt",
        "DUAL_CLUTCH": "dual_clutch",
        "MANUAL": "manual",
    }

    def normalize_row(
        self,
        row: CsvRow,
        field_mapping: FieldMapping | None,
    ) -> CsvRow:
        """Map and normalize USA Car CSV values for vehicle persistence."""
        normalized = super().normalize_row(row, field_mapping)
        normalized["make"] = self.map_provider_value(
            normalized.get("make"),
            self.make_mapping,
        )
        normalized["body_style"] = self.map_provider_value(
            normalized.get("body_style"),
            self.body_style_mapping,
        )
        normalized["fuel_type"] = self.map_provider_value(
            normalized.get("fuel_type"),
            self.fuel_type_mapping,
        )
        normalized["transmission"] = self.map_provider_value(
            normalized.get("transmission"),
            self.transmission_mapping,
        )
        normalized["price"] = self.cents_to_price(normalized.get("price"))
        return normalized

    def map_provider_value(
        self,
        value: str | None,
        mapping: dict[str, str],
    ) -> str:
        """Map a USA Car enum to a platform value."""
        if value is None or not value.strip():
            return ""
        return mapping.get(value.strip().upper(), "other")

    def cents_to_price(self, value: str | None) -> str | None:
        """Convert USA Car integer cents into decimal currency units."""
        if value is None or not value.strip():
            return None
        try:
            cents = Decimal(value)
        except InvalidOperation:
            return value
        return f"{cents / Decimal(100):.2f}"
