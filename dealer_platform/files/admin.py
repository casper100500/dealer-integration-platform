from django.contrib import admin

from dealer_platform.files.models import File


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = [
        "original_name",
        "file",
        "source_url",
        "content_type",
        "size",
        "created_at",
    ]
    search_fields = ["original_name", "file", "source_url"]
    readonly_fields = ["created_at", "updated_at"]
