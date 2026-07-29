.PHONY: up up-usa-car migrate superuser test lint

USA_CAR_COMPOSE = docker compose -f services/usa_car/compose.yml

up:
	docker compose up --build

up-usa-car:
	$(USA_CAR_COMPOSE) up --build

migrate:
	docker compose run --rm web python manage.py migrate

superuser:
	docker compose run --rm web python manage.py createsuperuser

test:
	docker compose up --detach --wait db redis
	docker compose run --rm --no-deps web pytest
	$(USA_CAR_COMPOSE) run --rm --no-deps usa-car pytest

lint:
	docker compose run --rm --no-deps web black --check .
	docker compose run --rm --no-deps web isort --check-only .
	docker compose run --rm --no-deps web flake8 .
	docker compose run --rm --no-deps web mypy .
	$(USA_CAR_COMPOSE) run --rm --no-deps usa-car black --check .
	$(USA_CAR_COMPOSE) run --rm --no-deps usa-car isort --check-only .
	$(USA_CAR_COMPOSE) run --rm --no-deps usa-car flake8 .
	$(USA_CAR_COMPOSE) run --rm --no-deps usa-car mypy app tests
