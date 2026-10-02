.DEFAULT_GOAL := help
IMAGE ?= cicd-pipeline:latest
# Host port. On macOS, AirPlay Receiver already listens on 5000: use e.g. `make dev PORT=5001`
PORT ?= 5000

.PHONY: help install dev lint format typecheck security test check build run up down clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Install the package with dev dependencies and git hooks
	pip install -e ".[dev]"
	pre-commit install

dev: ## Run the Flask dev server with auto-reload
	flask --app app.main run --debug --port $(PORT)

lint: ## Lint and check formatting (same as CI)
	ruff check .
	ruff format --check .

format: ## Auto-fix lint issues and format code
	ruff check --fix .
	ruff format .

typecheck: ## Static type checking
	mypy app tests

security: ## Static security analysis (SAST)
	bandit -r app/

test: ## Run tests with coverage
	pytest --cov=app --cov-report=term-missing

check: lint typecheck security test ## Run every CI quality gate locally

build: ## Build the production image
	docker build --target runner -t $(IMAGE) .

run: ## Run the production image
	docker run --rm -p $(PORT):5000 $(IMAGE)

up: ## Start the dev stack (hot-reload) with docker compose
	PORT=$(PORT) docker compose up --build

down: ## Stop the dev stack
	docker compose down

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage coverage.xml htmlcov *.egg-info
