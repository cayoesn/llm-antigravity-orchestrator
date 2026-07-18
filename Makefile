.PHONY: install run test lint coverage docker-up docker-down docker-logs

install:
	poetry install

run:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	poetry run pytest

lint:
	poetry run ruff check app tests || true

coverage:
	poetry run pytest --cov=app tests/

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f
