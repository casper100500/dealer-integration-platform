.PHONY: up migrate superuser test lint

up:
	docker compose up --build

migrate:
	docker compose run --rm web python manage.py migrate

superuser:
	docker compose run --rm web python manage.py createsuperuser

test:
	docker compose run --rm web pytest

lint:
	docker compose run --rm web black --check .
	docker compose run --rm web isort --check-only .
	docker compose run --rm web flake8 .
	docker compose run --rm web mypy .
