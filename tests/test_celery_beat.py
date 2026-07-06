"""Tests for database-backed Celery Beat scheduling."""

from __future__ import annotations

import json

import pytest
from django.conf import settings
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from dealer_platform.integrations import tasks


def test_database_scheduler_is_configured() -> None:
    """Use django-celery-beat as the project's periodic task scheduler."""
    assert settings.CELERY_BEAT_SCHEDULER == (
        "django_celery_beat.schedulers:DatabaseScheduler"
    )


@pytest.mark.django_db
def test_usacar_task_can_be_scheduled_by_config_name() -> None:
    """Store a periodic USA Car task using its named configuration."""
    interval = IntervalSchedule.objects.create(
        every=15,
        period=IntervalSchedule.MINUTES,
    )

    periodic_task = PeriodicTask.objects.create(
        name="Import Demo USA Car",
        task=tasks.task_fetch_usacar_inventory.name,
        interval=interval,
        kwargs=json.dumps({"UsaCarConfig": "Demo USA Car"}),
    )

    assert periodic_task.task == (
        "dealer_platform.integrations.tasks.task_fetch_usacar_inventory"
    )
    assert json.loads(periodic_task.kwargs) == {"UsaCarConfig": "Demo USA Car"}
