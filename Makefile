.PHONY: dev migrate docker-up shell test

dev:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker-compose up -d

migrate:
	psql "$(DATABASE_URL)" -f migrations/000_init.sql

shell:
	poetry shell

test:
	poetry run pytest -q
