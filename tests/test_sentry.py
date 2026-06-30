"""Tests for Sentry error-monitoring configuration."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from config import sentry


def test_sentry_is_not_initialized_without_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify an empty DSN keeps error reporting disabled."""
    init_mock = Mock()
    monkeypatch.setattr(sentry.sentry_sdk, "init", init_mock)

    sentry.initialize_sentry(
        dsn="",
        environment="test",
        release=None,
        traces_sample_rate=0.0,
    )

    init_mock.assert_not_called()


def test_sentry_is_initialized_with_django_and_celery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify configured monitoring covers web requests and async tasks."""
    init_mock = Mock()
    monkeypatch.setattr(sentry.sentry_sdk, "init", init_mock)

    sentry.initialize_sentry(
        dsn="https://public@example.com/1",
        environment="staging",
        release="dealer-platform@abc123",
        traces_sample_rate=0.25,
    )

    init_mock.assert_called_once()
    options = init_mock.call_args.kwargs
    assert options["dsn"] == "https://public@example.com/1"
    assert options["environment"] == "staging"
    assert options["release"] == "dealer-platform@abc123"
    assert options["traces_sample_rate"] == 0.25
    assert options["send_default_pii"] is False
    assert any(
        isinstance(integration, DjangoIntegration)
        for integration in options["integrations"]
    )
    assert any(
        isinstance(integration, CeleryIntegration)
        for integration in options["integrations"]
    )
