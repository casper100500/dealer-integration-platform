"""Sentry error-monitoring configuration."""

from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration


def initialize_sentry(
    *,
    dsn: str,
    environment: str,
    release: str | None,
    traces_sample_rate: float,
) -> None:
    """Initialize Sentry when an event-ingestion DSN is configured."""
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
    )
