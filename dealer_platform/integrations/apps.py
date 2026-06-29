from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    """Configure the external integrations Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "dealer_platform.integrations"
    verbose_name = "Integrations"
