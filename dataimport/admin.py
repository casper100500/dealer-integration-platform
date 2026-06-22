from django.contrib import admin

from dataimport.models import (
    VehicaleDataImport,
    VehicaleDataImportError,
    VehicaleDataImportWarning,
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


@admin.register(VehicaleDataImport)
class VehicaleDataImportAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "dealer",
        "source",
        "status",
        "parsed",
        "records_total",
        "records_created",
        "records_updated",
        "records_skipped",
        "skipped",
        "created_at",
    ]
    list_filter = ["dealer", "source", "status", "skipped"]
    search_fields = ["dealer__name", "file__original_name", "file__source_url"]
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
