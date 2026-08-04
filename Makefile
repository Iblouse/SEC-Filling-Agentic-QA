.PHONY: install test lint typecheck check

install:
	python -m pip install -e ".[dev]"

test:
	pytest --cov=edgar_qa --cov-report=term-missing

lint:
	ruff check src tests
	ruff format --check src tests

typecheck:
	mypy src

check: lint typecheck test
