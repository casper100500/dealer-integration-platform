from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import Any, cast

from django.db import transaction
from django.utils import timezone

from dealer_platform.dataimport.models import (
    ImportSource,
    VehicleDataImport,
    VehicleDataImportColumn,
)
from dealer_platform.files.utils import save_rows_as_csv_file
from dealer_platform.integrations.models import USACarIntegrationConfig
from dealer_platform.integrations.usacar.client import (
    USACarClient,
    USACarRecord,
)

USACarClientFactory = Callable[[USACarIntegrationConfig], USACarClient]


class USACarImportService:
    """Fetch USA Car inventory and create a CSV-backed import record."""

    manufacturer_mapping = {
        "M-04": "ford",
        "M-17": "toyota",
    }
    body_style_mapping = {
        11: "sedan",
        22: "hatchback",
        33: "wagon",
        44: "suv",
        55: "coupe",
        66: "convertible",
        77: "pickup",
        88: "van",
    }
    fuel_type_mapping = {
        "B": "plug_in_hybrid",
        "D": "diesel",
        "E": "electric",
        "H": "hybrid",
        "L": "lpg",
        "P": "gasoline",
    }
    transmission_mapping = {
        0: "automatic",
        1: "cvt",
        2: "dual_clutch",
        3: "manual",
    }
    currency_mapping = {
        840: "USD",
        978: "EUR",
    }

    def __init__(
        self,
        config: USACarIntegrationConfig,
        *,
        client_factory: USACarClientFactory = USACarClient,
    ) -> None:
        """Initialize the service with its integration dependencies."""
        self.config = config
        self.client_factory = client_factory

    def run_data_import(self) -> VehicleDataImport:
        """Fetch inventory, store its CSV, and create a queued import."""
        with self.client_factory(self.config) as client:
            records = client.fetch_inventory()

        rows = [self.transform_record(record) for record in records]
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"usacar_inventory_{timestamp}.csv"

        with transaction.atomic():
            stored_file = save_rows_as_csv_file(
                rows,
                filename=filename,
                source_url=(
                    f"{self.config.base_url.rstrip('/')}/"
                    f"{USACarClient.inventory_path}"
                ),
            )
            return VehicleDataImport.objects.create(
                dealer=self.config.dealer,
                source=ImportSource.usacar,
                file=stored_file,
            )

    def transform_record(self, record: USACarRecord) -> dict[str, object]:
        """Flatten one USA Car response record into a CSV dictionary."""
        identifiers = self._object(record, "identifiers")
        description = self._object(record, "description")
        specification = self._object(record, "specification")
        asking_price = self._object(record, "asking_price")

        return {
            "source_vehicle_id": self._value(record, "vehicle_id"),
            VehicleDataImportColumn.vin.value: self._value(
                identifiers,
                "vin_code",
            ),
            VehicleDataImportColumn.plate_number.value: self._value(
                identifiers,
                "registration",
            ),
            VehicleDataImportColumn.year.value: self._value(
                description,
                "model_year",
            ),
            VehicleDataImportColumn.make.value: self._mapped_value(
                description,
                "manufacturer_code",
                self.manufacturer_mapping,
            ),
            VehicleDataImportColumn.model.value: self._value(
                description,
                "name",
            ),
            VehicleDataImportColumn.exterior_color.value: self._value(
                specification,
                "paint",
            ),
            VehicleDataImportColumn.body_style.value: self._mapped_value(
                specification,
                "body_code",
                self.body_style_mapping,
            ),
            VehicleDataImportColumn.fuel_type.value: self._mapped_value(
                specification,
                "fuel_code",
                self.fuel_type_mapping,
            ),
            VehicleDataImportColumn.engine.value: self._value(
                specification,
                "motor",
            ),
            VehicleDataImportColumn.transmission.value: self._mapped_value(
                specification,
                "transmission_code",
                self.transmission_mapping,
            ),
            VehicleDataImportColumn.price.value: self._cents_to_price(
                self._value(asking_price, "amount_cents")
            ),
            VehicleDataImportColumn.currency.value: self._mapped_value(
                asking_price,
                "currency_code",
                self.currency_mapping,
            ),
        }

    def _object(
        self,
        data: dict[str, Any],
        field_name: str,
    ) -> dict[str, Any]:
        """Return a required nested USA Car JSON object."""
        value = data.get(field_name)
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an object")
        return cast(dict[str, Any], value)

    def _value(
        self,
        data: dict[str, Any],
        field_name: str,
    ) -> object:
        """Return a scalar USA Car value suitable for a CSV cell."""
        value = data.get(field_name)
        if value is None or isinstance(value, (str, int)):
            return value
        raise ValueError(f"{field_name} must be a string or integer")

    def _mapped_value(
        self,
        data: dict[str, Any],
        field_name: str,
        mapping: Mapping[Any, str],
    ) -> str:
        """Translate an opaque USA Car code into a standardized value."""
        value = self._value(data, field_name)
        try:
            return mapping[value]
        except KeyError as error:
            raise ValueError(
                f"{field_name} has unsupported code {value!r}"
            ) from error

    def _cents_to_price(self, value: object) -> str:
        """Convert an integer USA Car cent amount into a decimal price."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("amount_cents must be an integer")
        return f"{Decimal(value) / Decimal(100):.2f}"
