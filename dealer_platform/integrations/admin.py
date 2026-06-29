from django.contrib import admin

from dealer_platform.integrations.models import USACarIntegrationConfig


@admin.register(USACarIntegrationConfig)
class USACarIntegrationConfigAdmin(admin.ModelAdmin):
    """Manage USA Car integration configurations."""

    list_display = ["dealer", "base_url", "login", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["dealer__name", "base_url", "login"]
