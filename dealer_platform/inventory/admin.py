from django.contrib import admin, messages
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.http.response import HttpResponseBase, HttpResponseRedirect
from django.urls import reverse
from django.utils.text import slugify
from import_export.admin import ExportMixin
from import_export.formats.base_formats import Format
from import_export.forms import ExportForm

from dealer_platform.inventory.export_resources import (
    DealerExportResource,
    VehicleExportResource,
)
from dealer_platform.inventory.models import Dealer, DealerOffer, Vehicle

DEALER_EXPORT_FILTER_PARAMETER = "dealer_offers__dealer__id__exact"


@admin.register(Dealer)
class DealerAdmin(ExportMixin, admin.ModelAdmin):
    export_form_class = ExportForm
    resource_classes = [DealerExportResource]
    list_display = ["name", "external_id", "website_url", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "external_id", "website_url"]


class DealerOfferInline(admin.TabularInline):
    model = DealerOffer
    extra = 1


@admin.register(Vehicle)
class VehicleAdmin(ExportMixin, admin.ModelAdmin):
    export_form_class = ExportForm
    resource_classes = [VehicleExportResource]
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

    def export_action(self, request: HttpRequest) -> HttpResponseBase:
        """Require a dealer filter before exporting vehicle import data."""
        if self.get_selected_dealer_id(request) is None:
            messages.error(
                request,
                "Select a dealer before exporting vehicle data.",
            )
            return HttpResponseRedirect(
                reverse(
                    f"admin:{self.opts.app_label}_{self.opts.model_name}"
                    "_changelist"
                )
            )

        return super().export_action(request)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Vehicle]:
        """Prefetch dealer offers for vehicle admin list and export usage."""
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("dealer_offers__dealer")

    def get_export_resource_kwargs(
        self,
        request: HttpRequest,
        **kwargs: object,
    ) -> dict[str, object]:
        """Pass the selected dealer filter into the vehicle export resource."""
        resource_kwargs = super().get_export_resource_kwargs(
            request,
            **kwargs,
        )
        resource_kwargs["dealer_id"] = self.get_selected_dealer_id(request)
        return resource_kwargs

    def get_export_filename(
        self,
        request: HttpRequest,
        queryset: QuerySet[Vehicle],
        file_format: Format,
    ) -> str:
        """Return a vehicle export filename that includes the dealer name."""
        dealer_name = self.get_selected_dealer_name(request)
        if dealer_name is None:
            return super().get_export_filename(
                request,
                queryset,
                file_format,
            )

        dealer_slug = slugify(dealer_name) or "dealer"
        return f"vehicle_export_{dealer_slug}.{file_format.get_extension()}"

    def get_selected_dealer_id(self, request: HttpRequest) -> int | None:
        """Return the selected dealer filter value from the admin request."""
        dealer_id = request.GET.get(DEALER_EXPORT_FILTER_PARAMETER)
        if dealer_id is None:
            return None

        try:
            return int(dealer_id)
        except ValueError:
            return None

    def get_selected_dealer_name(self, request: HttpRequest) -> str | None:
        """Return the selected dealer name from the admin request filter."""
        dealer_id = self.get_selected_dealer_id(request)
        if dealer_id is None:
            return None

        return (
            Dealer.objects.filter(id=dealer_id)
            .values_list(
                "name",
                flat=True,
            )
            .first()
        )

    @admin.display(description="Dealers")
    def dealers(self, obj: Vehicle) -> str:
        """Display dealer names for the vehicle in the admin list."""
        return ", ".join(
            offer.dealer.name for offer in obj.dealer_offers.all()
        )
