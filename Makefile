.PHONY: install sync lint format test run migrate docker-up docker-down clean

install:
	uv sync --extra dev

pre-commit-install:
  uvx pre-commit install

sync:
	uv sync

lint:
	uv run ruff check src tests
	uv run mypy src

format:
	uv run ruff format src tests

test:
	uv run pytest -v

run:
	uv run python main.py

migrate:
	uv run alembic upgrade head

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf .venv uv.lock
	find . -type d -name __pycache__ -exec rm -rf {} +
