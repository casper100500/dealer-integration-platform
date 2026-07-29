"""API and feed models for the USA Car service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel


@dataclass(frozen=True)
class VehicleRecord:
    """Represent one validated vehicle from the active supplier feed."""

    vehicle_id: str
    vin_code: str
    registration: str
    manufacturer_code: str
    name: str
    model_year: int
    paint: str
    body_code: int
    fuel_code: str
    transmission_code: int
    motor: str
    amount_cents: int
    currency_code: int
    status: str

    def as_api_record(self) -> dict[str, object]:
        """Convert this feed record to USA Car's public API shape."""
        return {
            "vehicle_id": self.vehicle_id,
            "identifiers": {
                "vin_code": self.vin_code,
                "registration": self.registration,
            },
            "description": {
                "manufacturer_code": self.manufacturer_code,
                "name": self.name,
                "model_year": self.model_year,
            },
            "specification": {
                "paint": self.paint,
                "body_code": self.body_code,
                "fuel_code": self.fuel_code,
                "transmission_code": self.transmission_code,
                "motor": self.motor,
            },
            "asking_price": {
                "amount_cents": self.amount_cents,
                "currency_code": self.currency_code,
            },
        }


class TokenRequest(BaseModel):
    """Describe credentials accepted by the token endpoint."""

    login: str
    password: str


class TokenResponse(BaseModel):
    """Describe a successful token response."""

    access_token: str
    token_type: str = "bearer"


class InventoryResponse(BaseModel):
    """Describe one page of public USA Car inventory."""

    inventory: list[dict[str, object]]
    next_cursor: str | None


class FeedStatusResponse(BaseModel):
    """Describe the currently active supplier feed."""

    filename: str
    imported_at: datetime
    total_rows: int
    available_rows: int
