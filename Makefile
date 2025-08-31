.PHONY: install dev test lint format typecheck serve clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest src/tests/ -v

lint:
	ruff check src/

format:
	black src/

typecheck:
	mypy src/catabus_mcp/

serve:
	python -m catabus_mcp.server

serve-http:
	python -m catabus_mcp.server --http

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf build dist *.egg-info

ingest: serve