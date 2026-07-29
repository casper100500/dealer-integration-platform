"""HTTP contract tests for the USA Car service."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
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


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """Provide a running service backed by an isolated inventory file."""
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

    with TestClient(app) as test_client:
        yield test_client


def test_health_contract(client: TestClient) -> None:
    """Report service readiness without requiring authentication."""
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_token_contract(client: TestClient) -> None:
    """Exchange valid dealer credentials for the configured bearer token."""
    response = client.post(
        "/v1/auth/token/",
        json={"login": "dealer", "password": "password"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "token",
        "token_type": "bearer",
    }


@pytest.mark.parametrize(
    ("login", "password"),
    [
        ("unknown", "password"),
        ("dealer", "wrong-password"),
    ],
)
def test_token_rejects_invalid_credentials(
    client: TestClient,
    login: str,
    password: str,
) -> None:
    """Reject a request when either dealer credential is incorrect."""
    response = client.post(
        "/v1/auth/token/",
        json={"login": login, "password": password},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid USA Car credentials."}


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "",
        "token",
        "Basic token",
        "bearer token",
        "Bearer wrong-token",
    ],
    ids=[
        "missing",
        "empty",
        "missing-scheme",
        "wrong-scheme",
        "wrong-scheme-case",
        "wrong-token",
    ],
)
def test_inventory_requires_valid_bearer_token(
    client: TestClient,
    authorization: str | None,
) -> None:
    """Reject missing, malformed, and incorrect authorization values."""
    headers = (
        {"Authorization": authorization} if authorization is not None else {}
    )

    response = client.get("/v1/inventory/", headers=headers)

    assert response.status_code == 401
    assert response.json() == {
        "detail": "A valid USA Car bearer token is required."
    }
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_inventory_contract(client: TestClient) -> None:
    """Return available inventory for the configured bearer token."""
    response = client.get(
        "/v1/inventory/",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "inventory": [
            {
                "vehicle_id": "USC-1",
                "identifiers": {
                    "vin_code": "VIN-1",
                    "registration": "TX-1",
                },
                "description": {
                    "manufacturer_code": "M-17",
                    "name": "RAV4",
                    "model_year": 2022,
                },
                "specification": {
                    "paint": "Blue",
                    "body_code": 44,
                    "fuel_code": "P",
                    "transmission_code": 0,
                    "motor": "2.5L",
                },
                "asking_price": {
                    "amount_cents": 2500000,
                    "currency_code": 840,
                },
            }
        ],
        "next_cursor": None,
    }


@pytest.mark.parametrize("cursor", ["not-a-cursor", "-1"])
def test_inventory_rejects_invalid_cursor(
    client: TestClient,
    cursor: str,
) -> None:
    """Return a readable client error for malformed pagination cursors."""
    response = client.get(
        "/v1/inventory/",
        params={"cursor": cursor},
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid pagination cursor."}


@pytest.mark.parametrize("limit", [0, 101])
def test_inventory_rejects_limit_outside_supported_range(
    client: TestClient,
    limit: int,
) -> None:
    """Reject page sizes outside the documented range of 1 through 100."""
    response = client.get(
        "/v1/inventory/",
        params={"limit": limit},
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-Admin-Key": "wrong-admin-key"}],
    ids=["missing", "invalid"],
)
def test_feed_status_requires_valid_admin_key(
    client: TestClient,
    headers: dict[str, str],
) -> None:
    """Protect feed metadata from missing and incorrect admin keys."""
    response = client.get("/internal/v1/feed/status/", headers=headers)

    assert response.status_code == 401
    assert response.json() == {
        "detail": "A valid USA Car administration key is required."
    }


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-Admin-Key": "wrong-admin-key"}],
    ids=["missing", "invalid"],
)
def test_feed_upload_requires_valid_admin_key(
    client: TestClient,
    headers: dict[str, str],
) -> None:
    """Protect supplier-feed replacement with the administration key."""
    response = client.post(
        "/internal/v1/feed/",
        headers=headers,
        files={"feed": ("inventory.csv", FEED)},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "A valid USA Car administration key is required."
    }


def test_feed_status_contract(client: TestClient) -> None:
    """Return metadata for the active feed to an authorized administrator."""
    response = client.get(
        "/internal/v1/feed/status/",
        headers={"X-Admin-Key": "admin"},
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "inventory.csv"
    assert response.json()["total_rows"] == 1
    assert response.json()["available_rows"] == 1
    assert response.json()["imported_at"]


def test_invalid_upload_does_not_replace_inventory(
    client: TestClient,
) -> None:
    """Return row errors and preserve the active feed after a bad upload."""
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
    assert status_response.json()["filename"] == "inventory.csv"
