from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from io import StringIO

from django.core.files.base import ContentFile

from dealer_platform.files.models import File


def save_rows_as_csv_file(
    rows: Sequence[Mapping[str, object]],
    *,
    filename: str,
    source_url: str = "",
) -> File:
    """Serialize dictionary rows and save them as a CSV-backed File."""
    fieldnames = list(
        dict.fromkeys(field_name for row in rows for field_name in row)
    )
    output = StringIO(newline="")
    if fieldnames:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    content = output.getvalue().encode("utf-8")
    stored_file = File.objects.create(
        source_url=source_url,
        original_name=filename,
        content_type="text/csv",
        size=len(content),
    )
    stored_file.file.save(
        filename,
        ContentFile(content),
        save=True,
    )
    return stored_file
