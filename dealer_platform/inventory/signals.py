"""Signal handlers that record vehicle audit log events."""

from __future__ import annotations

from typing import Any, cast

from django.db.models.signals import (
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import receiver

from dealer_platform.inventory.audit import (
    AUDIT_OBJECT_ID_ATTRIBUTE,
    OpenSearchAuditError,
    VehicleAuditEventAction,
    send_vehicle_audit_event,
    vehicle_change_set,
    vehicle_create_changes,
    vehicle_delete_changes,
    vehicle_snapshot,
)
from dealer_platform.inventory.models import Vehicle

OLD_SNAPSHOT_ATTRIBUTE = "_audit_old_snapshot"


@receiver(pre_save, sender=Vehicle)
def capture_vehicle_before_save(
    sender: type[Vehicle],
    instance: Vehicle,
    **kwargs: object,
) -> None:
    """Capture existing vehicle values before a save."""
    if instance.pk is None:
        return

    previous_vehicle = Vehicle.objects.filter(pk=instance.pk).first()
    if previous_vehicle is None:
        return

    setattr(
        instance,
        OLD_SNAPSHOT_ATTRIBUTE,
        vehicle_snapshot(previous_vehicle),
    )


@receiver(post_save, sender=Vehicle)
def log_vehicle_after_save(
    sender: type[Vehicle],
    instance: Vehicle,
    created: bool,
    **kwargs: object,
) -> None:
    """Send an audit event after a vehicle is saved."""
    new_snapshot = vehicle_snapshot(instance)
    if created:
        try:
            send_vehicle_audit_event(
                VehicleAuditEventAction.CREATED,
                instance,
                vehicle_create_changes(new_snapshot),
            )
        except OpenSearchAuditError:
            return
        return

    old_snapshot = cast(
        dict[str, Any],
        getattr(instance, OLD_SNAPSHOT_ATTRIBUTE, {}),
    )
    changes = vehicle_change_set(old_snapshot, new_snapshot)
    if not changes:
        return

    try:
        send_vehicle_audit_event(
            VehicleAuditEventAction.UPDATED,
            instance,
            changes,
        )
    except OpenSearchAuditError:
        return


@receiver(pre_delete, sender=Vehicle)
def capture_vehicle_before_delete(
    sender: type[Vehicle],
    instance: Vehicle,
    **kwargs: object,
) -> None:
    """Capture vehicle values before deletion."""
    setattr(instance, AUDIT_OBJECT_ID_ATTRIBUTE, instance.pk)
    setattr(instance, OLD_SNAPSHOT_ATTRIBUTE, vehicle_snapshot(instance))


@receiver(post_delete, sender=Vehicle)
def log_vehicle_after_delete(
    sender: type[Vehicle],
    instance: Vehicle,
    **kwargs: object,
) -> None:
    """Send an audit event after a vehicle is deleted."""
    old_snapshot = cast(
        dict[str, Any],
        getattr(instance, OLD_SNAPSHOT_ATTRIBUTE, vehicle_snapshot(instance)),
    )
    try:
        send_vehicle_audit_event(
            VehicleAuditEventAction.DELETED,
            instance,
            vehicle_delete_changes(old_snapshot),
        )
    except OpenSearchAuditError:
        return
