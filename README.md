# Dealer Inventory ETL

A backend service for importing, validating, normalizing, and synchronizing vehicle inventory from multiple data sources.

For now, this project intentionally starts small: Django, PostgreSQL, and Docker. Other pieces can be added later when their purpose is clear.

## Local Development

Dependencies are managed with uv in `pyproject.toml` and `uv.lock`.

Start the stack:

```bash
docker compose up --build
```

The Django application will be available at:

- `http://localhost:8000/health/`
- `http://localhost:8000/api/v1/dealers/`
- `http://localhost:8000/api/v1/vehicles/`
- `http://localhost:8000/swagger/`

Vehicle data imports are processed by the Celery worker service. Keep the
`worker` and `redis` services running with the web service when testing import
processing locally.

Optional: copy the example environment file if you want to customize local settings:

```bash
cp .env.example .env
```

Run Django management commands through the web service:

```bash
docker compose run --rm web python manage.py check
```

Run formatting and lint checks:

```bash
docker compose run --rm web black --check .
docker compose run --rm web isort --check-only .
docker compose run --rm web flake8 .
docker compose run --rm web mypy .
```

Add a Python dependency:

```bash
uv add package-name
```

After dependencies change, rebuild the Docker image:

```bash
docker compose build web
```

Create a Django superuser:

```bash
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py createsuperuser
```

Then log in at:

- `http://localhost:8000/admin/`

## Services

- `web`: Django application
- `worker`: Celery worker for asynchronous import processing
- `db`: PostgreSQL 18.4
- `redis`: Celery broker/result backend

## PostgreSQL

The database runs as the `db` service in `docker-compose.yml`.

If you already have local data in `./.postgres_data` from an older
PostgreSQL major version, dump and restore it before starting the upgraded
container. PostgreSQL data directories are not reusable across major versions.

Django connects to it using these environment variables:

```text
POSTGRES_DB=dealer_inventory
POSTGRES_USER=dealer_inventory
POSTGRES_PASSWORD=dealer_inventory
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

Inside Docker, the hostname is `db` because that is the Compose service name.
