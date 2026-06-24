from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from rest_framework.test import APIClient

from inventory.models import Dealer, InventoryListing, Vehicle


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def dealer() -> Dealer:
    return Dealer.objects.create(
        name="Northside Motors",
        external_id="northside",
        website_url="https://northside.example.com",
    )


@pytest.fixture
def vehicle() -> Vehicle:
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


def paginated_results(response_data: dict[str, Any]) -> list[dict[str, Any]]:
    return list(response_data["results"])


@pytest.mark.django_db
def test_dealers_api_is_read_only(
    api_client: APIClient,
    dealer: Dealer,
) -> None:
    list_response = api_client.get("/api/dealers/")
    detail_response = api_client.get(f"/api/dealers/{dealer.pk}/")
    create_response = api_client.post(
        "/api/dealers/",
        {"name": "Downtown Cars"},
        format="json",
    )

    assert list_response.status_code == 200
    assert paginated_results(list_response.json())[0]["id"] == dealer.pk
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "Northside Motors"
    assert create_response.status_code == 405


@pytest.mark.django_db
def test_vehicle_api_crud(api_client: APIClient) -> None:
    create_response = api_client.post(
        "/api/vehicles/",
        {
            "vin": "2T3WFREV0FW654321",
            "plate_number": "XYZ987",
            "year": 2022,
            "make": "toyota",
            "model": "RAV4",
            "exterior_color": "Blue",
            "body_style": "suv",
            "fuel_type": "hybrid",
            "engine": "2.5L I4 Hybrid",
            "transmission": "automatic",
        },
        format="json",
    )

    assert create_response.status_code == 201
    vehicle_id = create_response.json()["id"]

    detail_response = api_client.get(f"/api/vehicles/{vehicle_id}/")
    patch_response = api_client.patch(
        f"/api/vehicles/{vehicle_id}/",
        {"exterior_color": "Black"},
        format="json",
    )
    list_response = api_client.get("/api/vehicles/")
    delete_response = api_client.delete(f"/api/vehicles/{vehicle_id}/")

    assert detail_response.status_code == 200
    assert detail_response.json()["vin"] == "2T3WFREV0FW654321"
    assert patch_response.status_code == 200
    assert patch_response.json()["exterior_color"] == "Black"
    assert list_response.status_code == 200
    assert paginated_results(list_response.json())[0]["id"] == vehicle_id
    assert delete_response.status_code == 204
    assert not Vehicle.objects.filter(pk=vehicle_id).exists()


@pytest.mark.django_db
def test_vehicle_dealer_listing_api(
    api_client: APIClient,
    dealer: Dealer,
    vehicle: Vehicle,
) -> None:
    listing_url = f"/api/vehicles/{vehicle.pk}/dealers/{dealer.pk}/listing/"

    create_response = api_client.post(
        listing_url,
        {"price": "21999.00", "currency": "USD"},
        format="json",
    )
    duplicate_response = api_client.post(
        listing_url,
        {"price": "21999.00", "currency": "USD"},
        format="json",
    )
    detail_response = api_client.get(listing_url)
    patch_response = api_client.patch(
        listing_url,
        {"price": "20999.00"},
        format="json",
    )
    delete_response = api_client.delete(listing_url)
    missing_response = api_client.get(listing_url)

    assert create_response.status_code == 201
    assert create_response.json()["dealer"]["id"] == dealer.pk
    assert create_response.json()["vehicle"]["id"] == vehicle.pk
    assert create_response.json()["price"] == "21999.00"
    assert create_response.json()["currency"] == "USD"
    assert duplicate_response.status_code == 400
    assert detail_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["price"] == "20999.00"
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404
    assert not InventoryListing.objects.filter(
        dealer=dealer,
        vehicle=vehicle,
    ).exists()


@pytest.mark.django_db
def test_vehicle_dealer_listing_validates_currency(
    api_client: APIClient,
    dealer: Dealer,
    vehicle: Vehicle,
) -> None:
    response = api_client.post(
        f"/api/vehicles/{vehicle.pk}/dealers/{dealer.pk}/listing/",
        {"price": "21999.00", "currency": "GBP"},
        format="json",
    )

    assert response.status_code == 400
    assert InventoryListing.objects.count() == 0


@pytest.mark.django_db
def test_vehicle_dealer_listing_stores_price_as_decimal(
    api_client: APIClient,
    dealer: Dealer,
    vehicle: Vehicle,
) -> None:
    response = api_client.post(
        f"/api/vehicles/{vehicle.pk}/dealers/{dealer.pk}/listing/",
        {"price": "21999.00", "currency": "USD"},
        format="json",
    )

    assert response.status_code == 201
    assert InventoryListing.objects.get().price == Decimal("21999.00")
