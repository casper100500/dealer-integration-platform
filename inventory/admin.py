from django.contrib import admin

from inventory.models import Dealer, Vehicle


@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ["name", "external_id", "website_url", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "external_id", "website_url"]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["vin", "year", "make", "model", "trim"]
    list_filter = ["make", "year", "fuel_type"]
    search_fields = ["vin", "make", "model", "trim"]
