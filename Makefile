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

lint:
	docker compose run --rm --no-deps web black --check .
	docker compose run --rm --no-deps web isort --check-only .
	docker compose run --rm --no-deps web flake8 .
	docker compose run --rm --no-deps web mypy .
