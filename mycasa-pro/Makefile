# MyCasa Pro - Development Makefile
# Usage: make <target>

.PHONY: help dev backend frontend test lint typecheck migrate clean install

# Default target
help:
	@echo "MyCasa Pro Development Commands"
	@echo ""
	@echo "  make install    - Install all dependencies"
	@echo "  make dev        - Start backend + frontend (parallel)"
	@echo "  make backend    - Start backend only (port 8000)"
	@echo "  make frontend   - Start frontend only (port 3000)"
	@echo "  make test       - Run all tests"
	@echo "  make lint       - Run linters"
	@echo "  make typecheck  - Run type checkers"
	@echo "  make migrate    - Run database migrations"
	@echo "  make clean      - Clean build artifacts"
	@echo ""

# Install dependencies
install:
	@echo "Installing Python dependencies..."
	cd . && python -m venv .venv || true
	. .venv/bin/activate && pip install -r requirements.txt
	@echo "Installing Node dependencies..."
	cd frontend && npm install
	@echo "✅ Dependencies installed"

# Development servers
dev:
	@echo "Starting MyCasa Pro in development mode..."
	@make -j2 backend frontend

backend:
	@echo "Starting backend on http://localhost:8000..."
	. .venv/bin/activate && uvicorn api.main_v2:app --reload --host 0.0.0.0 --port 8000

backend-legacy:
	@echo "Starting legacy backend on http://localhost:8000..."
	. .venv/bin/activate && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	@echo "Starting frontend on http://localhost:3000..."
	cd frontend && npm run dev

# Testing
test:
	@echo "Running tests..."
	. .venv/bin/activate && pytest tests/ -v --tb=short

test-coverage:
	@echo "Running tests with coverage..."
	. .venv/bin/activate && pytest tests/ -v --cov=. --cov-report=html

# Linting
lint:
	@echo "Running linters..."
	. .venv/bin/activate && ruff check . --fix || true
	cd frontend && npm run lint || true

lint-check:
	@echo "Checking lint (no fix)..."
	. .venv/bin/activate && ruff check .
	cd frontend && npm run lint

# Type checking
typecheck:
	@echo "Running type checkers..."
	. .venv/bin/activate && mypy --ignore-missing-imports agents/ api/ core/ || true
	cd frontend && npm run typecheck || true

# Database
migrate:
	@echo "Running database migrations..."
	. .venv/bin/activate && alembic upgrade head

migrate-create:
	@echo "Creating new migration..."
	@read -p "Migration name: " name; \
	. .venv/bin/activate && alembic revision --autogenerate -m "$$name"

migrate-downgrade:
	@echo "Downgrading one migration..."
	. .venv/bin/activate && alembic downgrade -1

db-reset:
	@echo "Resetting database..."
	rm -f data/mycasa.db
	. .venv/bin/activate && python -c "from database import init_db; init_db()"
	@echo "✅ Database reset"

# Cleanup
clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ 2>/dev/null || true
	cd frontend && rm -rf .next/ 2>/dev/null || true
	@echo "✅ Cleaned"

# Quick status check
status:
	@echo "=== MyCasa Pro Status ==="
	@curl -s http://localhost:8000/health 2>/dev/null | jq . || echo "Backend: not running"
	@curl -s http://localhost:3000 2>/dev/null > /dev/null && echo "Frontend: running on :3000" || echo "Frontend: not running"

# Acceptance tests
acceptance:
	@echo "Running acceptance tests..."
	@bash scripts/acceptance_test.sh
