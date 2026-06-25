from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from import_export.forms import ExportForm

from dealer_platform.inventory.admin import (
    DEALER_FILTER_PARAMETER,
    DealerAdmin,
    VehicleAdmin,
)
from dealer_platform.inventory.export_resources import (
    DealerExportResource,
    VEHICLE_EXPORT_FIELDS,
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


@pytest.mark.django_db
def test_dealer_export_resource_exports_dealer_data(dealer: Dealer) -> None:
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


def test_export_admins_do_not_show_field_selection() -> None:
    """Verify admin export forms do not include field-selection controls."""
    assert DealerAdmin.export_form_class is ExportForm
    assert VehicleAdmin.export_form_class is ExportForm


def test_vehicle_export_resource_accepts_import_export_kwargs() -> None:
    """Verify import-export internal resource kwargs are accepted."""
    resource = VehicleExportResource(dealer_id=42, force_native_type=True)

    assert resource.dealer_id == 42


@pytest.mark.django_db
def test_vehicle_export_resource_matches_import_standard_for_selected_dealer(
    dealer: Dealer,
    vehicle: Vehicle,
) -> None:
    """Verify vehicle export matches import headers for one selected dealer."""
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
    assert dataset.dict[0]["price"] == "21999.00"
    assert dataset.dict[0]["currency"] == "USD"


def test_vehicle_admin_passes_selected_dealer_to_export_resource() -> None:
    """Verify the dealer changelist filter is passed to the export resource."""
    request = RequestFactory().get(
        "/admin/inventory/vehicle/export/",
        {DEALER_FILTER_PARAMETER: "42"},
    )
    admin = VehicleAdmin(Vehicle, AdminSite())

    assert admin.get_selected_dealer_id(request) == 42
    assert admin.get_export_resource_kwargs(request)["dealer_id"] == 42
