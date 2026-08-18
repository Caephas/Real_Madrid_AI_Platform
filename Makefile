# ============================================
# Real Madrid AI Platform — Makefile
# ============================================

.PHONY: setup dev test pipeline lint clean help refresh

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------- Setup ----------

setup: ## First-time setup: start DB, run migrations, install deps
	docker compose up -d db
	@sleep 3
	alembic upgrade head
	pip install -e ".[dev]"
	@echo "Setup complete. Backend: http://localhost:8000 (DeepSeek LLM by default)"

# ---------- Development ----------

start: ## Start everything: db + backend + frontend (single command)
	docker compose up -d db
	@echo "PostgreSQL ready on :5433"
	@echo "Checking if team_stats need refresh..."
	@python3 -m pipeline.refresh_stats --check-only 2>/dev/null && \
		echo "Stats are stale — refreshing in background..." && \
		python3 -m pipeline.refresh_stats & \
	|| echo "Stats are fresh, skipping refresh"
	uvicorn app.main:app --reload --port 8000 &
	@sleep 2
	cd frontend && npm run dev

dev: ## Start db (and ollama if LLM_PROVIDER=ollama), run backend locally with hot reload
	docker compose up -d db
	@if [ "$${LLM_PROVIDER:-deepseek}" = "ollama" ]; then docker compose up -d ollama; fi
	uvicorn app.main:app --reload --port 8000

dev-all: ## Start all services (containerized)
	docker compose up --build

dev-frontend: ## Start frontend dev server
	cd frontend && npm run dev

# ---------- Database ----------

db-migrate: ## Run Alembic migrations
	alembic upgrade head

db-revision: ## Create a new Alembic migration (usage: make db-revision MSG="add users table")
	alembic revision --autogenerate -m "$(MSG)"

db-reset: ## Drop and recreate database
	docker compose down -v
	docker compose up -d db
	@sleep 3
	alembic upgrade head

# ---------- Pipeline ----------

pipeline: ## Run the full data pipeline: scrape → clean → train → update stats
	python3 -m pipeline.scrape --output data/raw/
	python3 -m pipeline.clean --input data/raw/ --output data/processed/
	python3 -m pipeline.train --input data/processed/ --output models/
	python3 -m pipeline.update_team_stats --input data/raw/la_liga_10_seasons.csv

fetch-season: ## Fetch the latest season from football-data.co.uk (no key needed) and merge
	python3 -m pipeline.fetch_season --merge

pipeline-train: ## Train model only (assumes cleaned data exists)
	python3 -m pipeline.train --input data/processed/ --output models/

refresh: ## Refresh team_stats: scrape current season from fbref, update rolling averages
	python3 -m pipeline.refresh_stats --force

# ---------- Quality ----------

test: ## Run tests
	pytest tests/ -v --tb=short

lint: ## Lint and format
	ruff check app/ pipeline/ tests/
	black --check app/ pipeline/ tests/

format: ## Auto-format code
	ruff check --fix app/ pipeline/ tests/
	black app/ pipeline/ tests/

# ---------- Cleanup ----------

clean: ## Stop containers and remove volumes
	docker compose down -v
	@echo "Cleaned up."

restart: ## Restart the app container (picks up new model files)
	docker compose restart app
