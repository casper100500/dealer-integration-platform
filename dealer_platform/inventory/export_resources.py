from __future__ import annotations

from decimal import Decimal
from typing import Any

from import_export import fields, resources

from dealer_platform.inventory.models import Dealer, DealerOffer, Vehicle

VEHICLE_EXPORT_FIELDS = (
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
    "dealer_id",
    "price",
    "currency",
)


class DealerExportResource(resources.ModelResource):
    class Meta:
        model = Dealer


class VehicleExportResource(resources.ModelResource):
    dealer_id = fields.Field(column_name="dealer_id")
    price = fields.Field(column_name="price")
    currency = fields.Field(column_name="currency")

    class Meta:
        model = Vehicle
        fields = VEHICLE_EXPORT_FIELDS
        export_order = VEHICLE_EXPORT_FIELDS

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the vehicle export resource for a selected dealer."""
        dealer_id = kwargs.pop("dealer_id", None)
        super().__init__(**kwargs)
        self.dealer_id = int(str(dealer_id)) if dealer_id is not None else None

    def get_dealer_offer(self, vehicle: Vehicle) -> DealerOffer | None:
        """Return the offer for the dealer selected in the admin filter."""
        if self.dealer_id is None:
            return None

        for offer in vehicle.dealer_offers.all():
            if offer.dealer_id == self.dealer_id:
                return offer

        return None

    def dehydrate_dealer_id(self, vehicle: Vehicle) -> str:
        """Export the selected dealer ID for the vehicle."""
        if self.get_dealer_offer(vehicle) is None:
            return ""

        return str(self.dealer_id)

    def dehydrate_price(self, vehicle: Vehicle) -> str:
        """Export the selected dealer offer price for the vehicle."""
        offer = self.get_dealer_offer(vehicle)
        if offer is None or offer.price is None:
            return ""

        price: Decimal = offer.price
        return str(price)

    def dehydrate_currency(self, vehicle: Vehicle) -> str:
        """Export the selected dealer offer currency for the vehicle."""
        offer = self.get_dealer_offer(vehicle)
        if offer is None:
            return ""

        return offer.currency
