"""HTTP contract tests for the USA Car service."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.inventory import InventoryStore
from app.main import create_app

FEED = (
    "vehicle_id,vin_code,registration,manufacturer_code,name,model_year,"
    "paint,body_code,fuel_code,transmission_code,motor,amount_cents,"
    "currency_code,status\n"
    "USC-1,VIN-1,TX-1,M-17,RAV4,2022,Blue,44,P,0,2.5L,2500000,840,"
    "available\n"
).encode()


def test_token_and_inventory_contract(tmp_path: Path) -> None:
    """Authenticate and retrieve inventory using the dealer API contract."""
    inventory_path = tmp_path / "inventory.csv"
    inventory_path.write_bytes(FEED)
    settings = Settings(
        inventory_path=inventory_path,
        api_login="dealer",
        api_password="password",
        access_token="token",
        admin_key="admin",
    )
    app = create_app(settings, InventoryStore(inventory_path))

    with TestClient(app) as client:
        token_response = client.post(
            "/v1/auth/token/",
            json={"login": "dealer", "password": "password"},
        )
        inventory_response = client.get(
            "/v1/inventory/",
            headers={"Authorization": "Bearer token"},
        )

    assert token_response.status_code == 200
    assert token_response.json()["access_token"] == "token"
    assert inventory_response.status_code == 200
    assert inventory_response.json()["inventory"][0]["vehicle_id"] == "USC-1"


def test_invalid_upload_does_not_replace_inventory(tmp_path: Path) -> None:
    """Return row errors and preserve the active feed after a bad upload."""
    inventory_path = tmp_path / "inventory.csv"
    inventory_path.write_bytes(FEED)
    settings = Settings(
        inventory_path=inventory_path,
        api_login="dealer",
        api_password="password",
        access_token="token",
        admin_key="admin",
    )
    app = create_app(settings, InventoryStore(inventory_path))

    with TestClient(app) as client:
        response = client.post(
            "/internal/v1/feed/",
            headers={"X-Admin-Key": "admin"},
            files={"feed": ("broken.csv", b"vehicle_id,status\n1,sold\n")},
        )
        status_response = client.get(
            "/internal/v1/feed/status/",
            headers={"X-Admin-Key": "admin"},
        )

    assert response.status_code == 422
    assert "Missing required columns" in response.json()["detail"][0]
    assert status_response.json()["total_rows"] == 1
