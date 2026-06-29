"""Tests for sample vehicle import files and import behavior.

This module verifies example CSV file shapes and confirms that importing
multiple dealer files shares repeated VINs while preserving dealer offers.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from django.core.files import File as DjangoFile

from dealer_platform.dataimport.models import (
    ImportSource,
    ImportStatus,
    VehicleDataImport,
)
from dealer_platform.dataimport.vehicle_loaders import VehicleDjangoLoader
from dealer_platform.files.models import File
from dealer_platform.inventory.models import Dealer, DealerOffer, Vehicle

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples" / "csv"
STANDARD_HEADER = [
    "vin",
    "plate_number",
    "year",
    "make",
    "model",
    "exterior_color",
    "body_style",
    "fuel_type",
    "engine",
    "transmission",
    "price",
    "currency",
]


def read_example_rows(filename: str) -> list[dict[str, str]]:
    """Read rows from an example vehicle import CSV file."""
    with (EXAMPLES_DIR / filename).open(newline="") as handle:
        return list(csv.DictReader(handle))


def create_import(
    filename: str,
    dealer: Dealer,
) -> VehicleDataImport:
    """Create a vehicle data import record backed by an example file."""
    source_path = EXAMPLES_DIR / filename
    stored_file = File.objects.create(
        original_name=filename,
        content_type="text/csv",
        size=source_path.stat().st_size,
    )

    with source_path.open("rb") as handle:
        stored_file.file.save(filename, DjangoFile(handle), save=True)

    return VehicleDataImport.objects.create(
        dealer=dealer,
        source=ImportSource.django,
        status=ImportStatus.in_progress,
        file=stored_file,
    )


@pytest.mark.parametrize(
    ("filename", "expected_rows"),
    [
        ("vehicle_import_dealer_northside.csv", 5),
        ("vehicle_import_dealer_lakeside.csv", 5),
        ("vehicle_import_dealer_downtown.csv", 5),
        ("vehicle_import_large_2,5k_records.csv", 2500),
    ],
)
def test_standard_example_files_have_expected_shape(
    filename: str,
    expected_rows: int,
) -> None:
    """Verify standard example files use the expected CSV shape."""
    rows = read_example_rows(filename)

    assert len(rows) == expected_rows
    assert rows
    assert list(rows[0].keys()) == STANDARD_HEADER
    assert all(list(row.keys()) == STANDARD_HEADER for row in rows)
    assert all(len(row["vin"]) <= 17 for row in rows)


def test_random_2500_row_example_has_unique_vins() -> None:
    """Verify the large random example file contains unique VINs."""
    rows = read_example_rows("vehicle_import_large_2,5k_records.csv")
    vins = [row["vin"] for row in rows]

    assert len(vins) == 2500
    assert len(set(vins)) == 2500


def test_dealer_examples_repeat_some_vins_across_files() -> None:
    """Verify dealer examples intentionally share selected VINs."""
    vins = Counter(
        row["vin"]
        for filename in [
            "vehicle_import_dealer_northside.csv",
            "vehicle_import_dealer_lakeside.csv",
            "vehicle_import_dealer_downtown.csv",
        ]
        for row in read_example_rows(filename)
    )

    assert {vin for vin, count in vins.items() if count > 1} == {
        "1HGCM82633A004352",
        "2T3WFREV0FW654321",
        "3VWFE21C04M000001",
        "JTDBR32E720123456",
        "KM8K12AA9KU765432",
    }


@pytest.mark.django_db
def test_importing_dealer_examples_shares_repeated_vins_between_dealers(
    settings: Any,
    tmp_path: Path,
) -> None:
    """Verify importing dealer examples shares vehicles and keeps offers."""
    settings.MEDIA_ROOT = tmp_path
    dealers = [
        Dealer.objects.create(name="Northside Motors"),
        Dealer.objects.create(name="Lakeside Autos"),
        Dealer.objects.create(name="Downtown Cars"),
    ]

    imports = [
        create_import("vehicle_import_dealer_northside.csv", dealers[0]),
        create_import("vehicle_import_dealer_lakeside.csv", dealers[1]),
        create_import("vehicle_import_dealer_downtown.csv", dealers[2]),
    ]

    for data_import in imports:
        VehicleDjangoLoader(data_import).run_parser()
        data_import.refresh_from_db()

        assert data_import.status == ImportStatus.done
        assert data_import.records_total == 5
        assert data_import.records_created == 5
        assert data_import.records_updated == 0
        assert data_import.records_skipped == 0
        assert data_import.errors.count() == 0

    assert Vehicle.objects.count() == 10
    assert DealerOffer.objects.count() == 15

    shared_vehicle = Vehicle.objects.get(vin="1HGCM82633A004352")
    assert shared_vehicle.dealer_offers.count() == 2
    assert set(
        shared_vehicle.dealer_offers.values_list("dealer__name", flat=True)
    ) == {"Northside Motors", "Lakeside Autos"}
