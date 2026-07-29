"""CSV validation, persistence, and inventory access."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from app.models import FeedStatusResponse, VehicleRecord

REQUIRED_COLUMNS = {
    "vehicle_id",
    "vin_code",
    "registration",
    "manufacturer_code",
    "name",
    "model_year",
    "paint",
    "body_code",
    "fuel_code",
    "transmission_code",
    "motor",
    "amount_cents",
    "currency_code",
    "status",
}
VALID_STATUSES = {"available", "sold", "unavailable"}


class FeedValidationError(ValueError):
    """Report one or more supplier-feed validation failures."""

    def __init__(self, errors: list[str]) -> None:
        """Initialize the exception with readable row errors."""
        super().__init__("Supplier feed validation failed.")
        self.errors = errors


@dataclass(frozen=True)
class ParsedFeed:
    """Hold validated records before they become the active snapshot."""

    records: tuple[VehicleRecord, ...]


def parse_feed(data: bytes) -> ParsedFeed:
    """Parse and validate a complete USA Car supplier CSV feed."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise FeedValidationError(
            ["The feed must be UTF-8 encoded."]
        ) from error

    reader = csv.DictReader(io.StringIO(text, newline=""))
    fieldnames = set(reader.fieldnames or [])
    missing_columns = sorted(REQUIRED_COLUMNS - fieldnames)
    if missing_columns:
        raise FeedValidationError(
            ["Missing required columns: " + ", ".join(missing_columns)]
        )

    records: list[VehicleRecord] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        try:
            record = _parse_row(row, row_number)
        except ValueError as error:
            errors.append(str(error))
            continue
        if record.vehicle_id in seen_ids:
            errors.append(
                f"Row {row_number}: duplicate vehicle_id "
                f"{record.vehicle_id!r}."
            )
            continue
        seen_ids.add(record.vehicle_id)
        records.append(record)

    if errors:
        raise FeedValidationError(errors)
    return ParsedFeed(records=tuple(records))


def _parse_row(row: dict[str, str | None], row_number: int) -> VehicleRecord:
    """Validate and convert one supplier-feed row."""
    vehicle_id = _required(row, "vehicle_id", row_number)
    status = _required(row, "status", row_number).lower()
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Row {row_number}: status must be one of "
            f"{', '.join(sorted(VALID_STATUSES))}."
        )

    model_year = _integer(row, "model_year", row_number)
    if not 1900 <= model_year <= 2100:
        raise ValueError(
            f"Row {row_number}: model_year must be between 1900 and 2100."
        )

    amount_cents = _integer(row, "amount_cents", row_number)
    if amount_cents < 0:
        raise ValueError(f"Row {row_number}: amount_cents cannot be negative.")

    return VehicleRecord(
        vehicle_id=vehicle_id,
        vin_code=_required(row, "vin_code", row_number),
        registration=_required(row, "registration", row_number),
        manufacturer_code=_required(
            row,
            "manufacturer_code",
            row_number,
        ),
        name=_required(row, "name", row_number),
        model_year=model_year,
        paint=_required(row, "paint", row_number),
        body_code=_integer(row, "body_code", row_number),
        fuel_code=_required(row, "fuel_code", row_number),
        transmission_code=_integer(
            row,
            "transmission_code",
            row_number,
        ),
        motor=_required(row, "motor", row_number),
        amount_cents=amount_cents,
        currency_code=_integer(row, "currency_code", row_number),
        status=status,
    )


def _required(
    row: dict[str, str | None],
    field: str,
    row_number: int,
) -> str:
    """Return a required, trimmed CSV value."""
    value = row.get(field)
    if value is None or not value.strip():
        raise ValueError(f"Row {row_number}: {field} is required.")
    return value.strip()


def _integer(
    row: dict[str, str | None],
    field: str,
    row_number: int,
) -> int:
    """Return a required CSV value parsed as an integer."""
    value = _required(row, field, row_number)
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(
            f"Row {row_number}: {field} must be an integer."
        ) from error


class InventoryStore:
    """Own the persisted supplier feed and parsed inventory snapshot."""

    def __init__(self, inventory_path: Path) -> None:
        """Initialize an empty store at the configured snapshot path."""
        self.inventory_path = inventory_path
        self._lock = RLock()
        self._records: tuple[VehicleRecord, ...] = ()
        self._filename = inventory_path.name
        self._imported_at = datetime.now(UTC)

    def load(self) -> None:
        """Load and validate the persisted inventory snapshot."""
        parsed = parse_feed(self.inventory_path.read_bytes())
        modified_at = datetime.fromtimestamp(
            self.inventory_path.stat().st_mtime,
            tz=UTC,
        )
        with self._lock:
            self._records = parsed.records
            self._filename = self.inventory_path.name
            self._imported_at = modified_at

    def replace(self, filename: str, data: bytes) -> FeedStatusResponse:
        """Validate and atomically activate a replacement supplier feed."""
        parsed = parse_feed(data)
        temporary_path = self.inventory_path.with_suffix(".tmp")
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_bytes(data)
        temporary_path.replace(self.inventory_path)

        with self._lock:
            self._records = parsed.records
            self._filename = Path(filename).name
            self._imported_at = datetime.now(UTC)
            return self._status_unlocked()

    def inventory_page(
        self,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[dict[str, object]], str | None]:
        """Return one page containing only available vehicles."""
        offset = self._parse_cursor(cursor)
        with self._lock:
            available = [
                record
                for record in self._records
                if record.status == "available"
            ]
            page = available[offset : offset + limit]
            next_offset = offset + len(page)
            next_cursor = (
                str(next_offset) if next_offset < len(available) else None
            )
            return (
                [record.as_api_record() for record in page],
                next_cursor,
            )

    def status(self) -> FeedStatusResponse:
        """Return metadata about the active supplier feed."""
        with self._lock:
            return self._status_unlocked()

    def _status_unlocked(self) -> FeedStatusResponse:
        """Build feed metadata while the caller holds the store lock."""
        return FeedStatusResponse(
            filename=self._filename,
            imported_at=self._imported_at,
            total_rows=len(self._records),
            available_rows=sum(
                record.status == "available" for record in self._records
            ),
        )

    def _parse_cursor(self, cursor: str | None) -> int:
        """Convert a public pagination cursor into a record offset."""
        if cursor is None:
            return 0
        try:
            offset = int(cursor)
        except ValueError as error:
            raise ValueError("Invalid pagination cursor.") from error
        if offset < 0:
            raise ValueError("Invalid pagination cursor.")
        return offset
