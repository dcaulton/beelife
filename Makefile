.PHONY: install sync lint format test run migrate alembic-revision docker-up docker-down clean

install:
	uv sync --extra dev
	uv pip install -e .

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
	uv run --with-editable . alembic upgrade head

alembic-revision:
	uv run --with-editable . alembic revision --autogenerate -m "$(m)"

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf .venv uv.lock
	find . -type d -name __pycache__ -exec rm -rf {} +

dev:
	uv run uvicorn beelife.main:app --reload --port 8120 --host 0.0.0.0
