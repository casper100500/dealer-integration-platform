# Dealer Inventory ETL

A backend service for importing, validating, normalizing, and synchronizing vehicle inventory from multiple data sources.

For now, this project intentionally starts small: Django, PostgreSQL, and Docker. Other pieces can be added later when their purpose is clear.

## Local Development

Start the stack:

```bash
docker compose up --build
```

The Django application will be available at:

- `http://localhost:8000/health/`

Optional: copy the example environment file if you want to customize local settings:

```bash
cp .env.example .env
```

Run Django management commands through the web service:

```bash
docker compose run --rm web python manage.py check
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
- `db`: PostgreSQL 16

## PostgreSQL

The database runs as the `db` service in `docker-compose.yml`.

Django connects to it using these environment variables:

```text
POSTGRES_DB=dealer_inventory
POSTGRES_USER=dealer_inventory
POSTGRES_PASSWORD=dealer_inventory
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

Inside Docker, the hostname is `db` because that is the Compose service name.
