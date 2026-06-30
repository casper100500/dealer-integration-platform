"""Tests for vehicle audit events sent to OpenSearch."""

from __future__ import annotations

from typing import Any, TypeAlias
from unittest.mock import Mock, patch

import httpx
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.test import override_settings
from rest_framework.test import APIClient

from dealer_platform.inventory.audit import (
    AUDIT_OBJECT_ID_ATTRIBUTE,
    OpenSearchAuditClient,
    OpenSearchAuditError,
    VehicleAuditEventAction,
    audit_actor,
    build_vehicle_audit_event,
)
from dealer_platform.inventory.models import Vehicle

UserModel: TypeAlias = type[AbstractUser]


@pytest.fixture
def user_model() -> UserModel:
    """Return the configured Django user model."""
    return get_user_model()


@pytest.fixture
def api_client(user_model: UserModel) -> APIClient:
    """Create an authenticated API client for audit tests."""
    user = user_model.objects.create_user(
        username="audit-user",
        password="correct-password",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def vehicle() -> Vehicle:
    """Create a vehicle used by audit tests."""
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


def build_client(
    responses: list[httpx.Response],
) -> tuple[OpenSearchAuditClient, list[httpx.Request]]:
    """Build an audit client backed by a mock OpenSearch transport."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        """Return queued OpenSearch responses and record requests."""
        requests.append(request)
        return responses.pop(0)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    audit_client = OpenSearchAuditClient(
        base_url="http://opensearch:9200",
        index_name="audit-test",
        timeout_seconds=1.0,
        client=http_client,
    )
    return audit_client, requests


class TestOpenSearchAuditClient:
    """Tests for direct OpenSearch audit event writes."""

    @pytest.mark.django_db
    def test_send_vehicle_event_creates_missing_index(
        self,
        vehicle: Vehicle,
    ) -> None:
        """Verify audit events create the OpenSearch index when missing."""
        audit_client, requests = build_client(
            [
                httpx.Response(404),
                httpx.Response(201),
                httpx.Response(201),
            ]
        )

        audit_client.send_vehicle_event(
            VehicleAuditEventAction.CREATED,
            vehicle,
            {"vin": {"old": None, "new": vehicle.vin}},
        )

        assert [request.method for request in requests] == [
            "HEAD",
            "PUT",
            "POST",
        ]
        assert requests[0].url.path == "/audit-test"
        assert requests[2].url.path == "/audit-test/_doc"

    @pytest.mark.django_db
    def test_send_vehicle_event_raises_for_opensearch_error(
        self,
        vehicle: Vehicle,
    ) -> None:
        """Verify OpenSearch failures raise audit errors."""
        audit_client, _requests = build_client(
            [httpx.Response(200), httpx.Response(500, text="boom")]
        )

        with pytest.raises(OpenSearchAuditError, match="write audit event"):
            audit_client.send_vehicle_event(
                VehicleAuditEventAction.CREATED,
                vehicle,
                {"vin": {"old": None, "new": vehicle.vin}},
            )

    @pytest.mark.django_db
    def test_build_vehicle_audit_event_includes_actor(
        self,
        user_model: UserModel,
        vehicle: Vehicle,
    ) -> None:
        """Verify audit event documents include authenticated actors."""
        user = user_model.objects.create_user(username="audit-user")

        with audit_actor(user):
            event = build_vehicle_audit_event(
                VehicleAuditEventAction.UPDATED,
                vehicle,
                {"model": {"old": "Camry", "new": "Corolla"}},
            )

        assert event["event_type"] == "inventory.vehicle.audit"
        assert event["action"] == VehicleAuditEventAction.UPDATED
        assert event["object_id"] == vehicle.pk
        assert event["object_repr"] == vehicle.vin
        assert event["vehicle_vin"] == vehicle.vin
        assert event["actor_id"] == user.pk
        assert event["actor_username"] == "audit-user"
        assert event["changes"] == {
            "model": {"old": "Camry", "new": "Corolla"},
        }


class TestVehicleAuditSignals:
    """Tests for vehicle model signals that emit audit events."""

    @pytest.mark.django_db
    @override_settings(OPENSEARCH_AUDIT_LOGS_ENABLED=True)
    def test_vehicle_create_sends_audit_event(self) -> None:
        """Verify vehicle creation sends a created audit event."""
        audit_client = Mock()

        with patch(
            "dealer_platform.inventory.audit.get_audit_client",
            return_value=audit_client,
        ):
            vehicle = Vehicle.objects.create(
                vin="2T3WFREV0FW654321",
                plate_number="XYZ987",
                year=2022,
                make="toyota",
                model="RAV4",
                exterior_color="Blue",
                body_style="suv",
                fuel_type="hybrid",
                engine="2.5L I4 Hybrid",
                transmission="automatic",
            )

        audit_client.send_vehicle_event.assert_called_once()
        action, event_vehicle, changes = (
            audit_client.send_vehicle_event.call_args.args
        )
        assert action == VehicleAuditEventAction.CREATED
        assert event_vehicle == vehicle
        assert changes["vin"] == {
            "old": None,
            "new": "2T3WFREV0FW654321",
        }

    @pytest.mark.django_db
    @override_settings(OPENSEARCH_AUDIT_LOGS_ENABLED=True)
    def test_vehicle_update_sends_changed_fields_only(
        self,
        vehicle: Vehicle,
    ) -> None:
        """Verify vehicle updates send only changed fields."""
        audit_client = Mock()

        with patch(
            "dealer_platform.inventory.audit.get_audit_client",
            return_value=audit_client,
        ):
            vehicle.model = "Corolla"
            vehicle.exterior_color = "Black"
            vehicle.save()

        action, event_vehicle, changes = (
            audit_client.send_vehicle_event.call_args.args
        )
        assert action == VehicleAuditEventAction.UPDATED
        assert event_vehicle == vehicle
        assert changes == {
            "model": {"old": "Camry", "new": "Corolla"},
            "exterior_color": {"old": "White", "new": "Black"},
        }

    @pytest.mark.django_db
    @override_settings(OPENSEARCH_AUDIT_LOGS_ENABLED=True)
    def test_vehicle_noop_save_does_not_send_audit_event(
        self,
        vehicle: Vehicle,
    ) -> None:
        """Verify unchanged vehicle saves do not emit audit events."""
        audit_client = Mock()

        with patch(
            "dealer_platform.inventory.audit.get_audit_client",
            return_value=audit_client,
        ):
            vehicle.save()

        audit_client.send_vehicle_event.assert_not_called()

    @pytest.mark.django_db
    @override_settings(OPENSEARCH_AUDIT_LOGS_ENABLED=True)
    def test_vehicle_delete_sends_audit_event(self, vehicle: Vehicle) -> None:
        """Verify vehicle deletion sends previous field values."""
        audit_client = Mock()
        vehicle_id = vehicle.pk
        vehicle_vin = vehicle.vin

        with patch(
            "dealer_platform.inventory.audit.get_audit_client",
            return_value=audit_client,
        ):
            vehicle.delete()

        action, event_vehicle, changes = (
            audit_client.send_vehicle_event.call_args.args
        )
        assert action == VehicleAuditEventAction.DELETED
        assert getattr(event_vehicle, AUDIT_OBJECT_ID_ATTRIBUTE) == vehicle_id
        assert event_vehicle.vin == vehicle_vin
        assert changes["vin"] == {"old": vehicle_vin, "new": None}


class TestVehicleAuditAPIContext:
    """Tests for actor capture through API requests."""

    @pytest.mark.django_db
    @override_settings(OPENSEARCH_AUDIT_LOGS_ENABLED=True)
    def test_vehicle_api_create_sends_actor(
        self,
        api_client: APIClient,
    ) -> None:
        """Verify API-created vehicle audit events include the user."""
        captured_events: list[dict[str, Any]] = []

        def capture_event(
            action: str,
            vehicle: Vehicle,
            changes: dict[str, dict[str, Any]],
        ) -> None:
            """Capture the built audit event for assertions."""
            captured_events.append(
                build_vehicle_audit_event(action, vehicle, changes)
            )

        audit_client = Mock()
        audit_client.send_vehicle_event.side_effect = capture_event

        with patch(
            "dealer_platform.inventory.audit.get_audit_client",
            return_value=audit_client,
        ):
            response = api_client.post(
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

        assert response.status_code == 201
        assert captured_events[0]["actor_username"] == "audit-user"
        assert captured_events[0]["action"] == VehicleAuditEventAction.CREATED
