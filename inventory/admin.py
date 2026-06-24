from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest

from inventory.models import Dealer, DealerOffer, Vehicle


@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ["name", "external_id", "website_url", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "external_id", "website_url"]


class DealerOfferInline(admin.TabularInline):
    model = DealerOffer
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
        "dealers",
    ]
    list_filter = [
        "dealer_offers__dealer",
        "make",
        "year",
        "body_style",
        "fuel_type",
    ]
    search_fields = [
        "vin",
        "plate_number",
        "make",
        "model",
        "dealer_offers__dealer__name",
    ]
    inlines = [DealerOfferInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Vehicle]:
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("dealer_offers__dealer")

    @admin.display(description="Dealers")
    def dealers(self, obj: Vehicle) -> str:
        return ", ".join(
            offer.dealer.name for offer in obj.dealer_offers.all()
        )
