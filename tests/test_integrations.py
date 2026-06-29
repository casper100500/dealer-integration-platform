"""Tests for external integration configuration models and admin."""

from __future__ import annotations

import pytest
from django.contrib import admin
from django.db import IntegrityError, transaction

from dealer_platform.integrations.admin import USACarIntegrationConfigAdmin
from dealer_platform.integrations.models import (
    AbstractIntegrationConfig,
    USACarIntegrationConfig,
)
from dealer_platform.inventory.models import Dealer


@pytest.fixture
def dealer() -> Dealer:
    """Create a dealer for integration configuration tests."""
    return Dealer.objects.create(
        name="Northside Motors",
        external_id="northside",
    )


@pytest.mark.django_db
class TestUSACarIntegrationConfig:
    """Verify USA Car integration configuration behavior."""

    def test_abstract_config_does_not_create_a_model_table(self) -> None:
        """Verify shared integration configuration remains abstract."""
        assert AbstractIntegrationConfig._meta.abstract is True

    def test_create_active_config_by_default(self, dealer: Dealer) -> None:
        """Verify a USA Car configuration is active when first created."""
        config = USACarIntegrationConfig.objects.create(
            dealer=dealer,
            base_url="https://api.usacar.example",
            login="northside-user",
            password="demo-password",
        )

        assert config.is_active is True
        assert str(config) == "USA Car integration for Northside Motors"

    def test_allow_only_one_config_per_dealer(self, dealer: Dealer) -> None:
        """Verify a dealer cannot have two USA Car configurations."""
        USACarIntegrationConfig.objects.create(
            dealer=dealer,
            base_url="https://api.usacar.example",
            login="northside-user",
            password="demo-password",
        )

        with pytest.raises(IntegrityError), transaction.atomic():
            USACarIntegrationConfig.objects.create(
                dealer=dealer,
                base_url="https://backup.usacar.example",
                login="backup-user",
                password="backup-password",
            )

    def test_config_can_disable_integration(self, dealer: Dealer) -> None:
        """Verify a USA Car integration can be switched off."""
        config = USACarIntegrationConfig.objects.create(
            dealer=dealer,
            base_url="https://api.usacar.example",
            login="northside-user",
            password="demo-password",
            is_active=False,
        )

        assert config.is_active is False


class TestUSACarIntegrationConfigAdmin:
    """Verify USA Car integration admin configuration."""

    def test_model_is_registered(self) -> None:
        """Verify the USA Car configuration is available in admin."""
        model_admin = admin.site._registry[USACarIntegrationConfig]

        assert isinstance(model_admin, USACarIntegrationConfigAdmin)

    def test_password_is_not_exposed_in_admin_lists(self) -> None:
        """Verify credentials are excluded from list and search settings."""
        model_admin = admin.site._registry[USACarIntegrationConfig]

        assert "password" not in model_admin.list_display
        assert "password" not in model_admin.search_fields
