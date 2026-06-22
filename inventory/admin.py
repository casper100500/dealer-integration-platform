from django.contrib import admin

from inventory.models import Dealer, InventoryListing, Vehicle


@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ["name", "external_id", "website_url", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "external_id", "website_url"]


class InventoryListingInline(admin.TabularInline):
    model = InventoryListing
    extra = 1


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        "vin",
        "plate_number",
        "year",
        "make",
        "model",
        "exterior_color",
    ]
    list_filter = ["make", "year", "body_style", "fuel_type"]
    search_fields = ["vin", "plate_number", "make", "model"]
    inlines = [InventoryListingInline]
