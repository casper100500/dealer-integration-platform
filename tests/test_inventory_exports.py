"""Tests for Django admin data exports.

This module verifies dealer and vehicle export resources, including vehicle
exports scoped to a selected dealer and formatted for vehicle data import.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from import_export.formats import base_formats
from import_export.forms import ExportForm

from dealer_platform.inventory.admin import (
    DEALER_EXPORT_FILTER_PARAMETER,
    DealerAdmin,
    VehicleAdmin,
)
from dealer_platform.inventory.export_resources import (
    VEHICLE_EXPORT_FIELDS,
    DealerExportResource,
    VehicleExportResource,
)
from dealer_platform.inventory.models import Dealer, DealerOffer, Vehicle


@pytest.fixture
def dealer() -> Dealer:
    """Create a dealer used by export resource tests."""
    return Dealer.objects.create(
        name="Northside Motors",
        external_id="northside",
        website_url="https://northside.example.com",
    )


@pytest.fixture
def vehicle() -> Vehicle:
    """Create a vehicle used by export resource tests."""
    return Vehicle.objects.create(
        vin="1HGCM82633A004352",
        plate_number="ABC123",
        year=2021,
        make="toyota",
        model="Camry",
        exterior_color="White",
        body_style="sedan",
        fuel_type="gasoline",
        engine="2.5L I4",
        transmission="automatic",
    )


class TestDealerExport:
    """Tests for dealer export resource behavior."""

    @pytest.mark.django_db
    def test_resource_exports_dealer_data(self, dealer: Dealer) -> None:
        """Verify dealer export uses the default dealer model fields."""
        dataset = DealerExportResource().export(Dealer.objects.all())

        assert set(dataset.headers) == {
            field.name for field in Dealer._meta.fields
        }
        assert dataset.dict[0]["name"] == "Northside Motors"
        assert dataset.dict[0]["external_id"] == "northside"
        assert dataset.dict[0]["website_url"] == (
            "https://northside.example.com"
        )


class TestExportAdmin:
    """Tests for shared Django admin export configuration."""

    def test_admins_do_not_show_field_selection(self) -> None:
        """Verify admin export forms do not include field-selection
        controls.
        """
        assert DealerAdmin.export_form_class is ExportForm
        assert VehicleAdmin.export_form_class is ExportForm


class TestVehicleExport:
    """Tests for vehicle export resource and admin behavior."""

    def test_resource_accepts_import_export_kwargs(self) -> None:
        """Verify import-export internal resource kwargs are accepted."""
        resource = VehicleExportResource(dealer_id=42, force_native_type=True)

        assert resource.dealer_id == 42

    @pytest.mark.django_db
    def test_resource_matches_import_standard_for_selected_dealer(
        self,
        dealer: Dealer,
        vehicle: Vehicle,
    ) -> None:
        """Verify vehicle export matches import headers for one dealer."""
        other_dealer = Dealer.objects.create(name="Lakeside Autos")
        DealerOffer.objects.create(
            dealer=dealer,
            vehicle=vehicle,
            price=Decimal("21999.00"),
            currency="USD",
        )
        DealerOffer.objects.create(
            dealer=other_dealer,
            vehicle=vehicle,
            price=Decimal("20999.00"),
            currency="EUR",
        )

        dataset = VehicleExportResource(dealer_id=dealer.id).export(
            Vehicle.objects.all()
        )

        assert dataset.headers == list(VEHICLE_EXPORT_FIELDS)
        assert dataset.dict[0]["vin"] == "1HGCM82633A004352"
        assert dataset.dict[0]["dealer_id"] == str(dealer.id)
        assert dataset.dict[0]["price"] == "21999.00"
        assert dataset.dict[0]["currency"] == "USD"

    def test_admin_passes_selected_dealer_to_export_resource(self) -> None:
        """Verify the dealer filter is passed to the export resource."""
        request = RequestFactory().get(
            "/admin/inventory/vehicle/export/",
            {DEALER_EXPORT_FILTER_PARAMETER: "42"},
        )
        admin = VehicleAdmin(Vehicle, AdminSite())

        assert admin.get_selected_dealer_id(request) == 42
        assert admin.get_export_resource_kwargs(request)["dealer_id"] == 42

    @pytest.mark.django_db
    def test_admin_export_filename_includes_dealer_name(
        self,
        dealer: Dealer,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify vehicle export filenames include dealer name and datetime."""
        monkeypatch.setattr(
            "dealer_platform.inventory.admin.timezone.now",
            lambda: datetime(
                2026,
                6,
                25,
                11,
                2,
                3,
                tzinfo=UTC,
            ),
        )
        request = RequestFactory().get(
            "/admin/inventory/vehicle/export/",
            {DEALER_EXPORT_FILTER_PARAMETER: str(dealer.id)},
        )
        admin = VehicleAdmin(Vehicle, AdminSite())

        filename = admin.get_export_filename(
            request,
            Vehicle.objects.none(),
            base_formats.CSV(),
        )

        assert filename == (
            "vehicle_export_northside-motors_20260625_110203.csv"
        )
