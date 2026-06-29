from __future__ import annotations

from config.celery import app as celery
from dealer_platform.integrations.models import USACarIntegrationConfig
from dealer_platform.integrations.usacar.service import USACarImportService

USACAR_CONFIG_NAME_KWARG = "UsaCarConfig"


@celery.task
def task_fetch_usacar_inventory(**kwargs: object) -> None:
    """Fetch inventory using the named USA Car configuration in kwargs."""
    integration_config_name = kwargs.get(USACAR_CONFIG_NAME_KWARG)
    if not isinstance(integration_config_name, str):
        raise ValueError(
            f"{USACAR_CONFIG_NAME_KWARG} must be a non-empty string."
        )
    integration_config_name = integration_config_name.strip()
    if not integration_config_name:
        raise ValueError(
            f"{USACAR_CONFIG_NAME_KWARG} must be a non-empty string."
        )

    integration_config = USACarIntegrationConfig.objects.filter(
        name=integration_config_name
    ).first()
    if integration_config is None:
        return

    USACarImportService(config=integration_config).run_data_import()
