.PHONY: help install dev test test-back test-front test-fast test-cov test-all migrate-create migrate-up migrate-down migrate-history migrate-current migrate-reset clean

# Settings are read from backend/.env (copy .env.example) or the process environment.

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies (including test deps)
	uv sync --extra test

dev: ## Run development server (reads backend/.env)
	uv run uvicorn app.main:app --reload --port 8000

# Testing (needs PostgreSQL; override with TEST_DATABASE_URL)
test: ## Run all tests (backend + frontend)
	uv run pytest tests/ -v
	cd ../frontend && pnpm test

test-back: ## Run backend tests only
	uv run pytest tests/ -v

test-front: ## Run frontend tests only
	cd ../frontend && pnpm test

test-all: ## Run all tests with verbose output
	@echo "━━━ Backend Tests ━━━"
	uv run pytest tests/ -v
	@echo ""
	@echo "━━━ Frontend Tests ━━━"
	cd ../frontend && pnpm test

test-fast: ## Run tests excluding slow ones
	uv run pytest tests/ -v -m "not slow"

test-cov: ## Run tests with coverage report
	uv run pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

# Database Migrations (DATABASE_URL from backend/.env or the environment)
migrate-create: ## Create a new migration (usage: make migrate-create MSG="your message")
	@if [ -z "$(MSG)" ]; then \
		echo "Error: MSG is required. Usage: make migrate-create MSG=\"your message\""; \
		exit 1; \
	fi
	uv run alembic revision --autogenerate -m "$(MSG)"

migrate-up: ## Apply all pending migrations
	uv run alembic upgrade head

migrate-down: ## Rollback last migration
	uv run alembic downgrade -1

migrate-history: ## Show migration history
	uv run alembic history --verbose

migrate-current: ## Show current migration version
	uv run alembic current

migrate-reset: ## Rollback all migrations
	uv run alembic downgrade base

# Utility
clean: ## Clean Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
