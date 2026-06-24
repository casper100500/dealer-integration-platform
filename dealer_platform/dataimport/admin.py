from typing import cast

from django.contrib import admin
from django.db.models import Count
from django.db.models.query import QuerySet
from django.http import HttpRequest

from dealer_platform.dataimport.models import (
    VehicleDataImport,
    VehicleDataImportError,
    VehicleDataImportParsingConfig,
    VehicleDataImportParsingConfigField,
    VehicleDataImportWarning,
)


class VehicleDataImportErrorInline(admin.TabularInline):
    model = VehicleDataImportError
    extra = 0
    readonly_fields = ["message", "row_number", "raw_data", "created_at"]
    can_delete = False


class VehicleDataImportWarningInline(admin.TabularInline):
    model = VehicleDataImportWarning
    extra = 0
    readonly_fields = ["message", "row_number", "raw_data", "created_at"]
    can_delete = False


class VehicleDataImportParsingConfigFieldInline(admin.TabularInline):
    model = VehicleDataImportParsingConfigField
    extra = 1


@admin.register(VehicleDataImportParsingConfig)
class VehicleDataImportParsingConfigAdmin(admin.ModelAdmin):
    list_display = ["name", "columns_to_skip"]
    search_fields = ["name", "fields__custom_field"]
    inlines = [VehicleDataImportParsingConfigFieldInline]


@admin.register(VehicleDataImport)
class VehicleDataImportAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "dealer",
        "source",
        "parsing_config",
        "status",
        "parsed",
        "records_total",
        "records_created",
        "records_updated",
        "records_skipped",
        "errors_count",
        "warnings_count",
        "skipped",
        "created_at",
    ]
    list_filter = ["dealer", "source", "parsing_config", "status", "skipped"]
    search_fields = [
        "dealer__name",
        "file__original_name",
        "file__source_url",
        "parsing_config__name",
    ]
    readonly_fields = [
        "skipped",
        "records_total",
        "records_created",
        "records_updated",
        "records_skipped",
        "errors_count",
        "warnings_count",
        "started_at",
        "finished_at",
        "parsed",
        "created_at",
        "updated_at",
    ]
    inlines = [
        VehicleDataImportErrorInline,
        VehicleDataImportWarningInline,
    ]

    def get_queryset(
        self,
        request: HttpRequest,
    ) -> QuerySet[VehicleDataImport]:
        queryset = super().get_queryset(request)
        return cast(
            QuerySet[VehicleDataImport],
            queryset.annotate(
                errors_count=Count("errors", distinct=True),
                warnings_count=Count("warnings", distinct=True),
            ),
        )

    @admin.display(ordering="errors_count", description="Errors")
    def errors_count(self, obj: VehicleDataImport) -> int:
        return int(getattr(obj, "errors_count", 0))

    @admin.display(ordering="warnings_count", description="Warnings")
    def warnings_count(self, obj: VehicleDataImport) -> int:
        return int(getattr(obj, "warnings_count", 0))
