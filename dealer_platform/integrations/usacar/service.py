from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from django.db import transaction
from django.utils import timezone

from dealer_platform.dataimport.models import ImportSource, VehicleDataImport
from dealer_platform.files.utils import save_rows_as_csv_file
from dealer_platform.integrations.models import USACarIntegrationConfig
from dealer_platform.integrations.usacar.client import (
    USACarClient,
    USACarRecord,
)

USACarClientFactory = Callable[[USACarIntegrationConfig], USACarClient]


class USACarImportService:
    """Fetch USA Car inventory and create a CSV-backed import record."""

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
            "vehicle_id": self._value(record, "vehicle_id"),
            "vin_code": self._value(identifiers, "vin_code"),
            "registration": self._value(identifiers, "registration"),
            "model_year": self._value(description, "model_year"),
            "manufacturer": self._value(description, "manufacturer"),
            "model_name": self._value(description, "name"),
            "paint": self._value(specification, "paint"),
            "category": self._value(specification, "category"),
            "fuel": self._value(specification, "fuel"),
            "gearbox": self._value(specification, "gearbox"),
            "motor": self._value(specification, "motor"),
            "amount_cents": self._value(
                asking_price,
                "amount_cents",
            ),
            "currency_code": self._value(
                asking_price,
                "currency_code",
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
