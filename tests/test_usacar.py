"""Tests for USA Car configuration, client, tasks, and imports."""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import httpx
import pytest
from django.test import override_settings

from dealer_platform.dataimport.models import ImportSource, ImportStatus
from dealer_platform.integrations import tasks
from dealer_platform.integrations.models import (
    USACarIntegrationConfig,
)
from dealer_platform.integrations.usacar import (
    USACarAuthenticationError,
    USACarClient,
    USACarConfigurationError,
    USACarImportService,
    USACarRequestError,
    USACarResponseError,
)
from dealer_platform.inventory.models import Dealer, DealerOffer, Vehicle

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples" / "usa_car"
USACAR_JSON_FIXTURE = EXAMPLES_DIR / "inventory_response.json"
USACAR_CSV_FIXTURE = EXAMPLES_DIR / "vehicle_import.csv"


@pytest.fixture
def dealer() -> Dealer:
    """Create a dealer for USA Car configuration tests."""
    return Dealer.objects.create(
        name="Northside Motors",
        external_id="northside",
    )


def usacar_config(
    *,
    is_active: bool = True,
) -> USACarIntegrationConfig:
    """Build an unsaved USA Car configuration for client tests."""
    return USACarIntegrationConfig(
        name="Northside USA Car",
        base_url="https://api.usacar.example/root",
        login="northside-user",
        password="demo-password",
        is_active=is_active,
    )


def load_usacar_json_fixture() -> dict[str, Any]:
    """Load the visible USA Car inventory response example."""
    with USACAR_JSON_FIXTURE.open(encoding="utf-8") as fixture_file:
        payload = json.load(fixture_file)
    return cast(dict[str, Any], payload)


def load_usacar_csv_rows() -> list[dict[str, str]]:
    """Load the admin-ready USA Car CSV example."""
    with USACAR_CSV_FIXTURE.open(newline="") as fixture_file:
        return list(csv.DictReader(fixture_file))


class TestUSACarClient:
    """Verify USA Car authentication and inventory retrieval."""

    def test_fetch_paginated_inventory(self) -> None:
        """Verify authentication, authorization, and cursor pagination."""
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            """Return token and inventory responses for the requested path."""
            requests.append(request)
            if request.url.path == "/root/v1/auth/token/":
                return httpx.Response(
                    200,
                    json={"access_token": "test-token"},
                )
            if request.url.params.get("cursor") == "page-2":
                return httpx.Response(
                    200,
                    json={
                        "inventory": [{"vehicle_id": "USC-2"}],
                        "next_cursor": None,
                    },
                )
            return httpx.Response(
                200,
                json={
                    "inventory": [{"vehicle_id": "USC-1"}],
                    "next_cursor": "page-2",
                },
            )

        with USACarClient(
            usacar_config(),
            transport=httpx.MockTransport(handler),
        ) as client:
            records = client.fetch_inventory()

        assert records == [
            {"vehicle_id": "USC-1"},
            {"vehicle_id": "USC-2"},
        ]
        assert len(requests) == 3
        assert requests[0].method == "POST"
        assert requests[0].url.path == "/root/v1/auth/token/"
        assert requests[1].headers["Authorization"] == "Bearer test-token"
        assert requests[2].url.params["cursor"] == "page-2"

    def test_retry_transient_response(self) -> None:
        """Verify Tenacity retries a transient HTTP response."""
        attempts = 0
        sleep = Mock()

        def handler(request: httpx.Request) -> httpx.Response:
            """Fail the first authentication attempt and then succeed."""
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(503)
            if request.url.path.endswith("/auth/token/"):
                return httpx.Response(
                    200,
                    json={"access_token": "test-token"},
                )
            return httpx.Response(
                200,
                json={"inventory": [], "next_cursor": None},
            )

        with USACarClient(
            usacar_config(),
            transport=httpx.MockTransport(handler),
            sleep=sleep,
            backoff_jitter=0,
        ) as client:
            assert client.fetch_inventory() == []

        assert attempts == 3
        sleep.assert_called_once_with(0.25)

    def test_retry_transport_failure_until_exhausted(self) -> None:
        """Verify retry exhaustion raises a stable client exception."""
        attempts = 0
        sleep = Mock()

        def handler(request: httpx.Request) -> httpx.Response:
            """Simulate an unavailable USA Car server."""
            nonlocal attempts
            attempts += 1
            raise httpx.ConnectError("server unavailable", request=request)

        with USACarClient(
            usacar_config(),
            transport=httpx.MockTransport(handler),
            sleep=sleep,
            backoff_jitter=0,
        ) as client:
            with pytest.raises(
                USACarRequestError,
                match="failed after 3 attempts",
            ):
                client.fetch_inventory()

        assert attempts == 3
        assert [call.args[0] for call in sleep.call_args_list] == [0.25, 0.5]

    def test_do_not_retry_rejected_credentials(self) -> None:
        """Verify authentication failures are reported without retries."""
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            """Reject the configured USA Car credentials."""
            nonlocal attempts
            attempts += 1
            return httpx.Response(401)

        with USACarClient(
            usacar_config(),
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(
                USACarAuthenticationError,
                match="rejected",
            ):
                client.fetch_inventory()

        assert attempts == 1

    def test_reject_invalid_inventory_payload(self) -> None:
        """Verify malformed provider inventory does not reach a loader."""

        def handler(request: httpx.Request) -> httpx.Response:
            """Return a token followed by a malformed inventory response."""
            if request.url.path.endswith("/auth/token/"):
                return httpx.Response(
                    200,
                    json={"access_token": "test-token"},
                )
            return httpx.Response(
                200,
                json={"inventory": "not-a-list", "next_cursor": None},
            )

        with USACarClient(
            usacar_config(),
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(
                USACarResponseError,
                match="inventory list",
            ):
                client.fetch_inventory()

    def test_reject_repeated_pagination_cursor(self) -> None:
        """Verify a broken provider cannot cause an infinite page loop."""

        def handler(request: httpx.Request) -> httpx.Response:
            """Return the same pagination cursor on every inventory page."""
            if request.url.path.endswith("/auth/token/"):
                return httpx.Response(
                    200,
                    json={"access_token": "test-token"},
                )
            return httpx.Response(
                200,
                json={"inventory": [], "next_cursor": "same-cursor"},
            )

        with USACarClient(
            usacar_config(),
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(
                USACarResponseError,
                match="repeated pagination cursor",
            ):
                client.fetch_inventory()

    def test_reject_inactive_integration(self) -> None:
        """Verify disabled integrations make no HTTP requests."""
        handler = Mock()

        with USACarClient(
            usacar_config(is_active=False),
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(
                USACarConfigurationError,
                match="inactive",
            ):
                client.fetch_inventory()

        handler.assert_not_called()


class TestUSACarImport:
    """Verify the complete USA Car import pipeline."""

    @pytest.mark.django_db(transaction=True)
    def test_fetch_parse_and_save_inventory(self, tmp_path: Path) -> None:
        """Verify JSON becomes CSV before the signal imports inventory."""
        dealer = Dealer.objects.create(
            name="Northside Motors",
            external_id="northside",
        )
        config = USACarIntegrationConfig.objects.create(
            name="my test config",
            dealer=dealer,
            base_url="https://api.usacar.example",
            login="northside-user",
            password="demo-password",
        )
        fixture_payload = load_usacar_json_fixture()
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            """Return authentication and visible fixture responses."""
            requests.append(request)
            if request.url.path == "/v1/auth/token/":
                return httpx.Response(
                    200,
                    json={"access_token": "fixture-token"},
                )
            return httpx.Response(200, json=fixture_payload)

        transport = httpx.MockTransport(handler)
        sleep = Mock()

        def client_factory(
            config: USACarIntegrationConfig,
        ) -> USACarClient:
            """Build the real client against the in-memory server."""
            return USACarClient(
                config,
                transport=transport,
                sleep=sleep,
                backoff_jitter=0,
            )

        with override_settings(MEDIA_ROOT=tmp_path):
            data_import = USACarImportService(
                config,
                client_factory=client_factory,
            ).run_data_import()

            stored_file = data_import.file
            assert stored_file is not None
            with stored_file.file.open("r") as csv_file:
                csv_rows = list(csv.DictReader(csv_file))

        data_import.refresh_from_db()
        assert data_import.source == ImportSource.usacar
        assert data_import.file is not None
        assert data_import.parsing_config is None
        assert data_import.status == ImportStatus.done
        assert data_import.records_total == 2
        assert data_import.records_created == 2
        assert data_import.records_updated == 0
        assert data_import.records_skipped == 0
        assert data_import.errors.count() == 0
        assert data_import.warnings.count() == 0

        assert data_import.file.content_type == "text/csv"
        assert data_import.file.original_name.startswith("usacar_inventory_")
        assert data_import.file.original_name.endswith(".csv")
        assert data_import.file.source_url == (
            "https://api.usacar.example/v1/inventory/"
        )
        assert csv_rows == load_usacar_csv_rows()

        rav4 = Vehicle.objects.get(vin="2T3WFREV0FW654321")
        assert rav4.plate_number == "TX-7842"
        assert rav4.year == 2022
        assert rav4.make == "toyota"
        assert rav4.model == "RAV4"
        assert rav4.exterior_color == "Ocean Blue"
        assert rav4.body_style == "suv"
        assert rav4.fuel_type == "gasoline"
        assert rav4.engine == "2.5L I4"
        assert rav4.transmission == "automatic"

        rav4_offer = DealerOffer.objects.get(
            dealer=dealer,
            vehicle=rav4,
        )
        assert rav4_offer.price == Decimal("25990.00")
        assert rav4_offer.currency == "USD"

        f150 = Vehicle.objects.get(vin="1FTFW1E50MFA12345")
        assert f150.year == 2021
        assert f150.make == "ford"
        assert f150.model == "F-150"
        assert f150.body_style == "pickup"
        assert f150.fuel_type == "diesel"

        f150_offer = DealerOffer.objects.get(
            dealer=dealer,
            vehicle=f150,
        )
        assert f150_offer.price == Decimal("38750.50")
        assert f150_offer.currency == "USD"

        assert len(requests) == 2
        assert requests[0].method == "POST"
        assert json.loads(requests[0].content) == {
            "login": "northside-user",
            "password": "demo-password",
        }
        assert requests[1].headers["Authorization"] == "Bearer fixture-token"
        sleep.assert_not_called()


class TestUSACarTasks:
    """Verify USA Car Celery task entry points."""

    @pytest.mark.django_db
    def test_fetch_task_resolves_named_config(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify the task resolves UsaCarConfig by its unique name."""
        dealer = Dealer.objects.create(
            name="Northside Motors",
            external_id="northside",
        )
        config = USACarIntegrationConfig.objects.create(
            name="my test config",
            dealer=dealer,
            base_url="https://api.usacar.example",
            login="northside-user",
            password="demo-password",
        )
        service = Mock()
        service_factory = Mock(return_value=service)
        monkeypatch.setattr(tasks, "USACarImportService", service_factory)

        result = tasks.task_fetch_usacar_inventory(
            **{"UsaCarConfig": "my test config"}
        )

        assert result is None
        service_factory.assert_called_once_with(config=config)
        service.run_data_import.assert_called_once_with()

    def test_fetch_task_requires_named_config_kwarg(self) -> None:
        """Verify the task rejects a missing configuration name."""
        with pytest.raises(ValueError, match="UsaCarConfig"):
            tasks.task_fetch_usacar_inventory()
