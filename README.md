# Dealer Integration Platform

A backend service for importing, validating, normalizing, and synchronizing vehicle inventory from multiple data sources.

This project demonstrates:

- Django REST API design
- Celery-based async import processing
- PostgreSQL data modeling
- CSV/API data ingestion
- Data validation and normalization
- OpenAPI/Swagger documentation
- Docker-based local development
- pytest, linting, formatting, and type checks

## Business Flow

Dealer sends inventory -> import job is created -> Celery processes file/API
data -> vehicles are validated and normalized -> results are saved -> import
status is exposed through the API and Django admin.

## Portfolio Note

This is a portfolio/demo project built to show backend engineering experience
with data integrations, asynchronous processing, and API design. It does not
contain proprietary code.

## Local Development

Dependencies are managed with uv in `pyproject.toml` and `uv.lock`.

Start the stack:

```bash
make up
```

The Django application will be available at:

- `http://localhost:8000/health/`
- `http://localhost:8000/api/v1/auth/token/`
- `http://localhost:8000/api/v1/auth/token/refresh/`
- `http://localhost:8000/api/v1/auth/token/verify/`
- `http://localhost:8000/api/v1/dealers/`
- `http://localhost:8000/api/v1/vehicles/`
- `http://localhost:8000/swagger/`
- `http://localhost:5601/` for OpenSearch Dashboards

Inventory API endpoints require JWT authentication. Create a Django user, then
request an access and refresh token pair:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"your-username","password":"your-password"}'
```

Send authenticated inventory requests with the access token:

```bash
curl http://localhost:8000/api/v1/vehicles/ \
  -H "Authorization: Bearer your-access-token"
```

The DRF browsable API does not accept a JWT pasted into the page. For browser
access, open `http://localhost:8000/api-auth/login/`, sign in with the Django
user's username and password, and you will be redirected to
`http://localhost:8000/api/v1/`.
To use an access token interactively instead, open
`http://localhost:8000/swagger/`, select **Authorize**, and enter the access
token.

Vehicle data imports are processed by the Celery worker service. Keep the
`celery` and `redis` services running with the web service when testing import
processing locally.

Vehicle create, update, and delete operations are sent to OpenSearch as
structured audit events. Each event stores the action, timestamp, changed
vehicle fields, and the authenticated API user when one is available.

Optional: copy the example environment file if you want to customize local settings:

```bash
cp .env.example .env
```

Run Django management commands through the web service:

```bash
docker compose run --rm web python manage.py check
```

Apply database migrations:

```bash
make migrate
```

Create a Django superuser:

```bash
make superuser
```

Run tests:

```bash
make test
```

Run formatting, lint, and type checks:

```bash
make lint
```

Add a Python dependency:

```bash
uv add package-name
```

After dependencies change, rebuild the Docker image:

```bash
docker compose build web
```

After creating a superuser, log in at:

- `http://localhost:8000/admin/`

## Services

- `web`: Django application
- `celery`: Celery worker for asynchronous import processing
- `db`: PostgreSQL 18.4
- `redis`: Celery broker/result backend
- `opensearch`: Stores structured vehicle audit events
- `opensearch-dashboards`: UI for inspecting audit events

## Error Monitoring

The Django web service and Celery worker report unhandled errors to Sentry when
`SENTRY_DSN` is configured. Error reporting is disabled when the DSN is empty.
Create a Sentry Python project, copy its DSN into `.env`, and restart the
application:

```text
SENTRY_DSN=https://public-key@your-sentry-host/project-id
SENTRY_ENVIRONMENT=development
SENTRY_RELEASE=dealer-platform@local
SENTRY_TRACES_SAMPLE_RATE=0.0
```

Performance tracing is disabled by default. To verify error ingestion without
adding a test-only endpoint, send a diagnostic event from the web container:

```bash
docker compose run --rm web python manage.py shell -c \
  'import sentry_sdk; sentry_sdk.capture_message("Dealer Platform test event")'
```

Fatal vehicle import errors are reported explicitly because the importer
persists those failures instead of re-raising them. Expected row validation
errors remain in the import error records and are not sent to Sentry.

## Audit Logs

Vehicle create, update, and delete events are written to the OpenSearch index
configured by `OPENSEARCH_AUDIT_INDEX`, which defaults to:

```text
dealer-platform-audit-logs
```

Open OpenSearch Dashboards at:

- `http://localhost:5601/`

Create a data view for `dealer-platform-audit-logs` and use `@timestamp` as
the time field. Audit event documents include field-level changes in this
shape:

```json
{
  "event_type": "inventory.vehicle.audit",
  "action": "updated",
  "vehicle_vin": "1HGCM82633A004352",
  "changes": {
    "model": {
      "old": "Camry",
      "new": "Corolla"
    }
  }
}
```

## PostgreSQL

The database runs as the `db` service in `docker-compose.yml` and stores data
in the bind-mounted `./.postgres_data` directory.

If Postgres rejects the default local credentials, reset only the existing
development role password without deleting database files:

```bash
docker compose exec db psql -U postgres -d postgres \
  -c "ALTER USER postgres WITH PASSWORD 'postgres';"
```

Django connects to it using these environment variables:

```text
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

Inside Docker, the hostname is `db` because that is the Compose service name.
