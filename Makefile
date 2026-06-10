.PHONY: up down logs governance build test lint install run-local

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api

governance:
	@docker compose exec api cat /data/governance/governance.jsonl

build:
	docker compose build

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check app tests

run-local:
	STORAGE_BACKEND=memory TELEMETRY_BACKENDS=log uv run --env-file .env uvicorn app.api.main:app --reload
