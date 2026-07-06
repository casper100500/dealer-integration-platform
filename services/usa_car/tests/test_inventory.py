"""Tests for USA Car supplier-feed parsing and storage."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.inventory import FeedValidationError, InventoryStore, parse_feed

HEADER = (
    "vehicle_id,vin_code,registration,manufacturer_code,name,model_year,"
    "paint,body_code,fuel_code,transmission_code,motor,amount_cents,"
    "currency_code,status\n"
)


def feed_bytes(*rows: str) -> bytes:
    """Build a complete UTF-8 supplier feed from CSV rows."""
    return (HEADER + "\n".join(rows) + "\n").encode()


def test_parse_feed_rejects_duplicate_vehicle_ids() -> None:
    """Reject duplicate provider identifiers in a complete snapshot."""
    row = (
        "USC-1,VIN-1,TX-1,M-17,RAV4,2022,Blue,44,P,0,"
        "2.5L,2500000,840,available"
    )

    with pytest.raises(FeedValidationError) as error:
        parse_feed(feed_bytes(row, row))

    assert "duplicate vehicle_id" in error.value.errors[0]


def test_replacement_is_atomic_when_validation_fails(
    tmp_path: Path,
) -> None:
    """Keep the active snapshot when its replacement is invalid."""
    inventory_path = tmp_path / "inventory.csv"
    original = feed_bytes(
        "USC-1,VIN-1,TX-1,M-17,RAV4,2022,Blue,44,P,0,"
        "2.5L,2500000,840,available"
    )
    inventory_path.write_bytes(original)
    store = InventoryStore(inventory_path)
    store.load()

    with pytest.raises(FeedValidationError):
        store.replace("broken.csv", b"vehicle_id,status\nUSC-2,available\n")

    assert inventory_path.read_bytes() == original
    assert store.status().total_rows == 1


def test_inventory_filters_status_and_paginates(tmp_path: Path) -> None:
    """Expose available vehicles using cursor-based pages."""
    inventory_path = tmp_path / "inventory.csv"
    inventory_path.write_bytes(
        feed_bytes(
            "USC-1,VIN-1,TX-1,M-17,RAV4,2022,Blue,44,P,0,"
            "2.5L,2500000,840,available",
            "USC-2,VIN-2,TX-2,M-04,F-150,2021,White,77,D,0,"
            "3.0L,3800000,840,sold",
            "USC-3,VIN-3,TX-3,M-04,Focus,2020,Black,22,P,3,"
            "2.0L,1800000,840,available",
        )
    )
    store = InventoryStore(inventory_path)
    store.load()

    first_page, next_cursor = store.inventory_page(None, 1)
    second_page, final_cursor = store.inventory_page(next_cursor, 1)

    assert [record["vehicle_id"] for record in first_page] == ["USC-1"]
    assert next_cursor == "1"
    assert [record["vehicle_id"] for record in second_page] == ["USC-3"]
    assert final_cursor is None
