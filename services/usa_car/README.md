# USA Car Service

USA Car is a fictional, independently deployable vehicle provider used by the
Dealer Integration Platform demo. It accepts complete supplier CSV snapshots,
validates and persists the latest accepted file, and exposes available
vehicles through an authenticated, paginated HTTP API.

The service deliberately uses a file rather than a database. Its purpose is
to demonstrate service ownership and an HTTP integration boundary without
adding unrelated infrastructure.

## Feed format

The active supplier snapshot uses these columns:

```csv
vehicle_id,vin_code,registration,manufacturer_code,name,model_year,paint,body_code,fuel_code,transmission_code,motor,amount_cents,currency_code,status
```

Every upload is validated in full before it replaces the current snapshot.
Duplicate vehicle IDs, missing values, malformed numbers, invalid statuses,
negative prices, and implausible model years reject the complete upload.
Accepted files survive container restarts in the `usa_car_data` Docker volume.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health/` | Service health check |
| `POST` | `/internal/v1/feed/` | Replace the supplier CSV snapshot |
| `GET` | `/internal/v1/feed/status/` | Inspect the active snapshot |
| `POST` | `/v1/auth/token/` | Obtain a dealer access token |
| `GET` | `/v1/inventory/` | Retrieve available inventory |

Supplier endpoints require the `X-Admin-Key` header. Inventory requires the
bearer token returned by the token endpoint. Development credentials are
defined in the root `.env.example`.
