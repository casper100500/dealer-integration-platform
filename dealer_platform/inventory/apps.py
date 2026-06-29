from django.apps import AppConfig


class InventoryConfig(AppConfig):
    """Configure the inventory Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "dealer_platform.inventory"

    def ready(self) -> None:
        """Register inventory signal handlers when Django starts."""
        from dealer_platform.inventory import signals  # noqa: F401
