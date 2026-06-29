from django.db import models


class AbstractIntegrationConfig(models.Model):
    """Provide configuration shared by every dealer integration."""

    dealer = models.OneToOneField(
        "inventory.Dealer",
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class USACarIntegrationConfig(AbstractIntegrationConfig):
    """Store connection configuration for a USA Car integration."""

    name = models.CharField(max_length=255, unique=True)
    base_url = models.URLField()
    login = models.CharField(max_length=255)
    password = models.CharField(max_length=255)

    class Meta:
        verbose_name = "USA Car integration config"
        verbose_name_plural = "USA Car integration configs"

    def __str__(self) -> str:
        """Return a readable dealer-specific configuration label."""
        return self.name
