FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/service \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /service

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY .flake8 pyproject.toml uv.lock ./
RUN uv sync --frozen --group dev --no-install-project

COPY app ./app
COPY tests ./tests
COPY data/current_inventory.csv /data/current_inventory.csv

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
