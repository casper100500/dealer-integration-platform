"""Tests for the inventory REST API.

This module verifies dealer read-only endpoints, vehicle CRUD behavior, and
dealer offer operations exposed through the API.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from rest_framework.test import APIClient

from dealer_platform.inventory.models import Dealer, DealerOffer, Vehicle


@pytest.fixture
def api_client() -> APIClient:
    """Create an API client for inventory endpoint tests."""
    return APIClient()


@pytest.fixture
def dealer() -> Dealer:
    """Create a dealer used by inventory API tests."""
    return Dealer.objects.create(
        name="Northside Motors",
        external_id="northside",
        website_url="https://northside.example.com",
    )


@pytest.fixture
def vehicle() -> Vehicle:
    """Create a vehicle used by inventory API tests."""
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
    """Return the result list from a paginated API response payload."""
    return list(response_data["results"])


class TestDealerAPI:
    """Tests for dealer REST API behavior."""

    @pytest.mark.django_db
    def test_dealers_api_is_read_only(
        self,
        api_client: APIClient,
        dealer: Dealer,
    ) -> None:
        """Verify dealer endpoints allow reads but reject creates."""
        list_response = api_client.get("/api/v1/dealers/")
        detail_response = api_client.get(f"/api/v1/dealers/{dealer.pk}/")
        create_response = api_client.post(
            "/api/v1/dealers/",
            {"name": "Downtown Cars"},
            format="json",
        )

        assert list_response.status_code == 200
        assert paginated_results(list_response.json())[0]["id"] == dealer.pk
        assert detail_response.status_code == 200
        assert detail_response.json()["name"] == "Northside Motors"
        assert create_response.status_code == 405


class TestVehicleAPI:
    """Tests for vehicle REST API behavior."""

    @pytest.mark.django_db
    def test_vehicle_api_crud(self, api_client: APIClient) -> None:
        """Verify vehicle endpoints support CRUD."""
        create_response = api_client.post(
            "/api/v1/vehicles/",
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

        detail_response = api_client.get(f"/api/v1/vehicles/{vehicle_id}/")
        patch_response = api_client.patch(
            f"/api/v1/vehicles/{vehicle_id}/",
            {"exterior_color": "Black"},
            format="json",
        )
        list_response = api_client.get("/api/v1/vehicles/")
        delete_response = api_client.delete(f"/api/v1/vehicles/{vehicle_id}/")

        assert detail_response.status_code == 200
        assert detail_response.json()["vin"] == "2T3WFREV0FW654321"
        assert patch_response.status_code == 200
        assert patch_response.json()["exterior_color"] == "Black"
        assert list_response.status_code == 200
        assert paginated_results(list_response.json())[0]["id"] == vehicle_id
        assert delete_response.status_code == 204
        assert not Vehicle.objects.filter(pk=vehicle_id).exists()


class TestVehicleDealerOfferAPI:
    """Tests for vehicle dealer offer REST API behavior."""

    @pytest.mark.django_db
    def test_vehicle_dealer_offer_api(
        self,
        api_client: APIClient,
        dealer: Dealer,
        vehicle: Vehicle,
    ) -> None:
        """Verify dealer offer endpoints support their expected lifecycle."""
        offer_url = f"/api/v1/vehicles/{vehicle.pk}/dealers/{dealer.pk}/offer/"

        create_response = api_client.post(
            offer_url,
            {"price": "21999.00", "currency": "USD"},
            format="json",
        )
        duplicate_response = api_client.post(
            offer_url,
            {"price": "21999.00", "currency": "USD"},
            format="json",
        )
        detail_response = api_client.get(offer_url)
        patch_response = api_client.patch(
            offer_url,
            {"price": "20999.00"},
            format="json",
        )
        delete_response = api_client.delete(offer_url)
        missing_response = api_client.get(offer_url)

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
        assert not DealerOffer.objects.filter(
            dealer=dealer,
            vehicle=vehicle,
        ).exists()

    @pytest.mark.django_db
    def test_vehicle_dealer_offer_validates_currency(
        self,
        api_client: APIClient,
        dealer: Dealer,
        vehicle: Vehicle,
    ) -> None:
        """Verify dealer offer writes reject unsupported currencies."""
        response = api_client.post(
            f"/api/v1/vehicles/{vehicle.pk}/dealers/{dealer.pk}/offer/",
            {"price": "21999.00", "currency": "GBP"},
            format="json",
        )

        assert response.status_code == 400
        assert DealerOffer.objects.count() == 0

    @pytest.mark.django_db
    def test_vehicle_dealer_offer_stores_price_as_decimal(
        self,
        api_client: APIClient,
        dealer: Dealer,
        vehicle: Vehicle,
    ) -> None:
        """Verify dealer offer prices are stored as decimals."""
        response = api_client.post(
            f"/api/v1/vehicles/{vehicle.pk}/dealers/{dealer.pk}/offer/",
            {"price": "21999.00", "currency": "USD"},
            format="json",
        )

        assert response.status_code == 201
        assert DealerOffer.objects.get().price == Decimal("21999.00")
