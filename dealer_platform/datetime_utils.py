from __future__ import annotations

from datetime import datetime

from django.utils import timezone

STANDARD_DATETIME_FORMAT = "%Y%m%d_%H%M%S"


def get_local_datetime(value: datetime) -> str:
    """Format a datetime in local time using the project standard format."""
    return timezone.localtime(value).strftime(STANDARD_DATETIME_FORMAT)
