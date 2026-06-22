# DB Structure Proposal

This PR should focus on the first durable database shape for dealer inventory
ETL. The goal is to support imports from multiple providers, keep raw source
records for audit/debugging, normalize vehicles into a stable catalog, and track
dealer-facing inventory listings over time.

## Core Entities

### dealers

Represents a dealership or dealer rooftop whose inventory is imported.

Important fields:

- `id`
- `name`
- `external_id`
- `website_url`
- `is_active`
- `created_at`
- `updated_at`

Constraints and indexes:

- Unique `external_id` when present.
- Index `name` for admin/search usage.

### data_sources

Represents a provider, feed, scraper, API integration, or file source.

Important fields:

- `id`
- `name`
- `source_type`
- `base_url`
- `is_active`
- `created_at`
- `updated_at`

Constraints and indexes:

- Unique `name`.
- Index `source_type`.

### import_runs

Tracks each ETL execution against a source and, optionally, one dealer.

Important fields:

- `id`
- `data_source_id`
- `dealer_id`
- `status`
- `started_at`
- `finished_at`
- `records_seen`
- `records_created`
- `records_updated`
- `records_failed`
- `error_message`
- `metadata`

Constraints and indexes:

- Index `(data_source_id, started_at)`.
- Index `(dealer_id, started_at)`.
- Index `status`.

### raw_inventory_records

Stores untouched source payloads and import-level parsing status. This table is
the audit trail for what arrived from a source.

Important fields:

- `id`
- `import_run_id`
- `dealer_id`
- `source_record_id`
- `payload`
- `payload_hash`
- `status`
- `error_message`
- `created_at`

Constraints and indexes:

- Unique `(import_run_id, source_record_id)` when `source_record_id` is present.
- Index `payload_hash` to detect repeated unchanged records.
- Index `(dealer_id, created_at)`.
- Index `status`.

### vehicles

Represents the normalized vehicle identity. This should be mostly independent
from a specific dealer listing.

Important fields:

- `id`
- `vin`
- `year`
- `make`
- `model`
- `trim`
- `body_style`
- `engine`
- `transmission`
- `drivetrain`
- `fuel_type`
- `created_at`
- `updated_at`

Constraints and indexes:

- Unique `vin` when present.
- Index `(make, model, year)`.

### inventory_listings

Represents a vehicle offered by a dealer at a point in time. A listing can
change price, mileage, status, and source details while still pointing to the
same normalized vehicle.

Important fields:

- `id`
- `dealer_id`
- `vehicle_id`
- `data_source_id`
- `latest_raw_record_id`
- `stock_number`
- `listing_url`
- `condition`
- `status`
- `price`
- `mileage`
- `exterior_color`
- `interior_color`
- `first_seen_at`
- `last_seen_at`
- `created_at`
- `updated_at`

Constraints and indexes:

- Unique `(dealer_id, stock_number)` when `stock_number` is present.
- Unique `(dealer_id, vehicle_id)` for active listings when VIN/vehicle identity
  is available.
- Index `(dealer_id, status)`.
- Index `(vehicle_id)`.
- Index `(last_seen_at)`.

### listing_snapshots

Stores observed listing values over time so price/mileage/status history is not
lost when `inventory_listings` is updated.

Important fields:

- `id`
- `inventory_listing_id`
- `raw_inventory_record_id`
- `observed_at`
- `status`
- `price`
- `mileage`
- `listing_url`
- `attributes`

Constraints and indexes:

- Index `(inventory_listing_id, observed_at)`.
- Index `(raw_inventory_record_id)`.

## Suggested Django App Boundary

Create one domain app for the first version:

- `inventory`

Initial model groups:

- Source/import tracking: `DataSource`, `ImportRun`, `RawInventoryRecord`
- Dealer domain: `Dealer`
- Vehicle domain: `Vehicle`, `InventoryListing`, `ListingSnapshot`

This keeps the early schema simple while leaving room to split import orchestral
logic into a separate app later if it grows.

## Status Values

Recommended enums:

- `ImportRun.status`: `pending`, `running`, `completed`, `completed_with_errors`,
  `failed`
- `RawInventoryRecord.status`: `pending`, `parsed`, `skipped`, `failed`
- `InventoryListing.status`: `available`, `sold`, `removed`, `unknown`
- `InventoryListing.condition`: `new`, `used`, `certified`, `unknown`

## Design Notes

- Keep raw payloads in `raw_inventory_records.payload` as JSONB so each source
  can be reprocessed when parsing logic improves.
- Keep mutable latest state in `inventory_listings`, and append historical
  observations to `listing_snapshots`.
- Treat `vehicles` as normalized identity and specs, not as dealer inventory.
- Prefer nullable fields over fake placeholder values for partial source data.
- Use timestamps on all long-lived domain tables.

## Open Approval Questions

1. Should `Dealer.external_id` be source-specific, or should dealer IDs be
   tracked through a separate mapping table per data source?
2. Should active duplicate inventory be allowed for the same dealer and vehicle,
   or should `(dealer, vehicle)` be unique for active listings?
3. Do we need image/media tables in the first DB pass, or should images stay as
   raw payload/listing attributes until the ETL flow proves the need?
4. Should vehicle options/features become normalized tables now, or remain JSON
   attributes on snapshots/listings for the first iteration?
