from django.db import models


class File(models.Model):
    file = models.FileField(upload_to="imports/")
    source_url = models.URLField(blank=True)
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        if self.original_name:
            return self.original_name

        return self.file.name or f"File {self.pk}"
