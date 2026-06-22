from django.contrib import admin

from dataimport.models import (
    VehicaleDataImport,
    VehicaleDataImportError,
    VehicaleDataImportWarning,
    VehicleDataImportParsingConfig,
    VehicleDataImportParsingConfigField,
)


class VehicaleDataImportErrorInline(admin.TabularInline):
    model = VehicaleDataImportError
    extra = 0
    readonly_fields = ["message", "row_number", "raw_data", "created_at"]
    can_delete = False


class VehicaleDataImportWarningInline(admin.TabularInline):
    model = VehicaleDataImportWarning
    extra = 0
    readonly_fields = ["message", "row_number", "raw_data", "created_at"]
    can_delete = False


class VehicleDataImportParsingConfigFieldInline(admin.TabularInline):
    model = VehicleDataImportParsingConfigField
    extra = 1


@admin.register(VehicleDataImportParsingConfig)
class VehicleDataImportParsingConfigAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name", "fields__custom_field"]
    inlines = [VehicleDataImportParsingConfigFieldInline]


@admin.register(VehicaleDataImport)
class VehicaleDataImportAdmin(admin.ModelAdmin):
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
        "started_at",
        "finished_at",
        "parsed",
        "created_at",
        "updated_at",
    ]
    inlines = [
        VehicaleDataImportErrorInline,
        VehicaleDataImportWarningInline,
    ]
