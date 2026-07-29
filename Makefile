.PHONY: up migrate superuser test lint

up:
	docker compose up --build

migrate:
	docker compose run --rm web python manage.py migrate

superuser:
	docker compose run --rm web python manage.py createsuperuser

test:
	docker compose up --detach --wait db redis
	docker compose run --rm --no-deps web pytest
	docker compose run --rm --no-deps usa-car pytest

lint:
	docker compose run --rm --no-deps web black --check .
	docker compose run --rm --no-deps web isort --check-only .
	docker compose run --rm --no-deps web flake8 .
	docker compose run --rm --no-deps web mypy .
	docker compose run --rm --no-deps usa-car black --check .
	docker compose run --rm --no-deps usa-car isort --check-only .
	docker compose run --rm --no-deps usa-car flake8 .
	docker compose run --rm --no-deps usa-car mypy app tests
