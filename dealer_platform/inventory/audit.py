"""Helpers for sending vehicle audit events to OpenSearch."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, cast

import httpx
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User
from django.utils import timezone

from dealer_platform.inventory.models import Vehicle

VEHICLE_AUDIT_FIELDS = [
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
]
AUDIT_OBJECT_ID_ATTRIBUTE = "_audit_object_id"

_current_actor: ContextVar[User | None] = ContextVar(
    "inventory_audit_actor",
    default=None,
)


@contextmanager
def audit_actor(
    actor: AbstractBaseUser | AnonymousUser | None,
) -> Iterator[None]:
    """Temporarily associate audit logs with the current actor."""
    authenticated_actor = None
    if actor is not None and actor.is_authenticated:
        authenticated_actor = cast(User, actor)

    token = _current_actor.set(authenticated_actor)
    try:
        yield
    finally:
        _current_actor.reset(token)


def get_current_audit_actor() -> User | None:
    """Return the actor associated with the current audit context."""
    return _current_actor.get()


def vehicle_snapshot(vehicle: Vehicle) -> dict[str, Any]:
    """Return auditable field values for a vehicle."""
    return {
        field_name: getattr(vehicle, field_name)
        for field_name in VEHICLE_AUDIT_FIELDS
    }


def vehicle_change_set(
    old_values: dict[str, Any],
    new_values: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return field-level old/new changes between two snapshots."""
    changes: dict[str, dict[str, Any]] = {}
    for field_name in VEHICLE_AUDIT_FIELDS:
        old_value = old_values.get(field_name)
        new_value = new_values.get(field_name)
        if old_value != new_value:
            changes[field_name] = {
                "old": old_value,
                "new": new_value,
            }

    return changes


def vehicle_create_changes(
    values: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return audit changes for a newly created vehicle."""
    return {
        field_name: {
            "old": None,
            "new": values.get(field_name),
        }
        for field_name in VEHICLE_AUDIT_FIELDS
    }


def vehicle_delete_changes(
    values: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return audit changes for a deleted vehicle."""
    return {
        field_name: {
            "old": values.get(field_name),
            "new": None,
        }
        for field_name in VEHICLE_AUDIT_FIELDS
    }


class VehicleAuditEventAction:
    """Define vehicle audit event action names."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


class OpenSearchAuditError(RuntimeError):
    """Represent a failure while writing audit events to OpenSearch."""


class OpenSearchAuditClient:
    """Write vehicle audit event documents to OpenSearch."""

    def __init__(
        self,
        base_url: str | None = None,
        index_name: str | None = None,
        timeout_seconds: float | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        """Create an OpenSearch audit client."""
        self.base_url = (base_url or settings.OPENSEARCH_URL).rstrip("/")
        self.index_name = index_name or settings.OPENSEARCH_AUDIT_INDEX
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.OPENSEARCH_TIMEOUT_SECONDS
        )
        self.client = client or httpx.Client(timeout=self.timeout_seconds)

    @property
    def index_url(self) -> str:
        """Return the full URL for the audit event index."""
        return f"{self.base_url}/{self.index_name}"

    @property
    def index_definition(self) -> dict[str, Any]:
        """Return OpenSearch mappings for audit event documents."""
        return {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                },
            },
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "event_type": {"type": "keyword"},
                    "action": {"type": "keyword"},
                    "object_type": {"type": "keyword"},
                    "object_id": {"type": "long"},
                    "object_repr": {"type": "keyword"},
                    "vehicle_vin": {"type": "keyword"},
                    "actor_id": {"type": "long"},
                    "actor_username": {"type": "keyword"},
                    "changes": {"type": "object", "enabled": True},
                },
            },
        }

    def ensure_index(self) -> None:
        """Create the audit event index when it does not exist."""
        try:
            response = self.client.head(self.index_url)
        except httpx.RequestError as exc:
            raise OpenSearchAuditError(str(exc)) from exc

        if response.status_code == 200:
            return

        if response.status_code != 404:
            self._raise_for_response(response, "check audit event index")

        try:
            create_response = self.client.put(
                self.index_url,
                json=self.index_definition,
            )
        except httpx.RequestError as exc:
            raise OpenSearchAuditError(str(exc)) from exc

        if create_response.status_code not in {200, 201}:
            self._raise_for_response(
                create_response,
                "create audit event index",
            )

    def send_vehicle_event(
        self,
        action: str,
        vehicle: Vehicle,
        changes: dict[str, dict[str, Any]],
    ) -> None:
        """Write a vehicle audit event to OpenSearch."""
        self.ensure_index()
        try:
            response = self.client.post(
                f"{self.index_url}/_doc",
                json=build_vehicle_audit_event(action, vehicle, changes),
            )
        except httpx.RequestError as exc:
            raise OpenSearchAuditError(str(exc)) from exc

        if response.status_code not in {200, 201}:
            self._raise_for_response(response, "write audit event")

    def _raise_for_response(
        self,
        response: httpx.Response,
        action: str,
    ) -> None:
        """Raise an audit error with OpenSearch response context."""
        msg = (
            f"Could not {action}: OpenSearch returned "
            f"{response.status_code} {response.text}"
        )
        raise OpenSearchAuditError(msg)


def build_vehicle_audit_event(
    action: str,
    vehicle: Vehicle,
    changes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a structured vehicle audit event document."""
    actor = get_current_audit_actor()
    object_id = getattr(vehicle, AUDIT_OBJECT_ID_ATTRIBUTE, vehicle.pk)
    return {
        "@timestamp": timezone.now().isoformat(),
        "event_type": "inventory.vehicle.audit",
        "action": action,
        "object_type": "inventory.Vehicle",
        "object_id": object_id,
        "object_repr": str(vehicle),
        "vehicle_vin": vehicle.vin,
        "actor_id": actor.pk if actor is not None else None,
        "actor_username": actor.username if actor is not None else None,
        "changes": changes,
    }


def get_audit_client() -> OpenSearchAuditClient:
    """Return the configured OpenSearch audit client."""
    return OpenSearchAuditClient()


def send_vehicle_audit_event(
    action: str,
    vehicle: Vehicle,
    changes: dict[str, dict[str, Any]],
) -> None:
    """Send a vehicle audit event when OpenSearch audit logs are enabled."""
    if not settings.OPENSEARCH_AUDIT_LOGS_ENABLED:
        return

    get_audit_client().send_vehicle_event(action, vehicle, changes)
