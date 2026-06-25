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
- `http://localhost:8000/api/v1/dealers/`
- `http://localhost:8000/api/v1/vehicles/`
- `http://localhost:8000/swagger/`

Vehicle data imports are processed by the Celery worker service. Keep the
`celery` and `redis` services running with the web service when testing import
processing locally.

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

## PostgreSQL

The database runs as the `db` service in `docker-compose.yml`.

If you already have local data in `./.postgres_data` from an older
PostgreSQL major version, dump and restore it before starting the upgraded
container. PostgreSQL data directories are not reusable across major versions.

Django connects to it using these environment variables:

```text
POSTGRES_DB=dealer_integration
POSTGRES_USER=dealer_integration
POSTGRES_PASSWORD=dealer_integration
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

Inside Docker, the hostname is `db` because that is the Compose service name.
