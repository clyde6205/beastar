# BeAstar.io - Makefile
# ========================
# Production-ready build and deployment commands

.PHONY: help install run test lint format docker docker-up docker-down docker-build docker-push

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

help: ## Show this help message
	@echo "BeAstar.io Makefile"
	@echo "=================="
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# Backend
install: ## Install Python dependencies
	@echo "$(BLUE)Installing Python dependencies...$(NC)"
	cd backend && pip install -r requirements.txt --upgrade
	@echo "$(GREEN)Dependencies installed!$(NC)"

run: ## Run the backend server
	@echo "$(BLUE)Starting BeAstar backend...$(NC)"
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run the backend in production mode
	@echo "$(BLUE)Starting BeAstar backend (production)...$(NC)"
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Celery
celery: ## Start Celery worker
	@echo "$(BLUE)Starting Celery worker...$(NC)"
	cd backend && celery -A app.worker worker --loglevel=INFO --concurrency=4

celery-beat: ## Start Celery beat (scheduled tasks)
	@echo "$(BLUE)Starting Celery beat...$(NC)"
	cd backend && celery -A app.worker beat --loglevel=INFO

# Testing
test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	cd backend && python -m pytest tests/ -v --tb=short

test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	cd backend && python -m pytest tests/backend/ -v

test-mobile: ## Run mobile tests
	@echo "$(BLUE)Running mobile tests...$(NC)"
	cd mobile && npm test

# Linting and Formatting
lint: ## Run linting
	@echo "$(BLUE)Running linter...$(NC)"
	cd backend && python -m ruff check .
	cd mobile && npm run lint

format: ## Format all code
	@echo "$(BLUE)Formatting code...$(NC)"
	cd backend && python -m black . && python -m ruff format .
	cd mobile && npm run format

# Docker
docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t beastar-backend:latest .
	@echo "$(GREEN)Docker image built!$(NC)"

docker-up: ## Start all services with Docker Compose
	@echo "$(BLUE)Starting services with Docker Compose...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started!$(NC)"

docker-down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)Services stopped!$(NC)"

docker-logs: ## Show logs for all services
	@echo "$(BLUE)Showing logs...$(NC)"
	docker-compose logs -f

docker-logs-backend: ## Show logs for backend service
	@echo "$(BLUE)Showing backend logs...$(NC)"
	docker-compose logs -f backend

docker-ps: ## Show running containers
	@echo "$(BLUE)Running containers:$(NC)"
	docker-compose ps

# Database
db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	cd backend && python -c "from app.db.supabase_client import setup_rpc_functions; setup_rpc_functions()"
	@echo "$(GREEN)Migrations complete!$(NC)"

db-setup: ## Setup database with RPC functions
	@echo "$(BLUE)Setting up RPC functions...$(NC)"
	cd backend && python -c "from app.db.supabase_client import setup_rpc_functions; setup_rpc_functions()"
	@echo "$(GREEN)RPC functions setup complete!$(NC)"

# Mobile
mobile-install: ## Install mobile dependencies
	@echo "$(BLUE)Installing mobile dependencies...$(NC)"
	cd mobile && npm install
	@echo "$(GREEN)Mobile dependencies installed!$(NC)"

mobile-run: ## Run mobile app
	@echo "$(BLUE)Starting mobile app...$(NC)"
	cd mobile && npx expo start

mobile-build-android: ## Build Android app
	@echo "$(BLUE)Building Android app...$(NC)"
	cd mobile && npx expo prebuild -p android && cd android && ./gradlew assembleRelease

mobile-build-ios: ## Build iOS app
	@echo "$(BLUE)Building iOS app...$(NC)"
	cd mobile && npx expo prebuild -p ios

# Cleanup
clean: ## Clean up build artifacts
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.log" -delete 2>/dev/null || true
	find . -name "*.tmp" -delete 2>/dev/null || true
	find . -name "*.orig" -delete 2>/dev/null || true
	find . -name "*.rej" -delete 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-docker: ## Clean up Docker containers and images
	@echo "$(BLUE)Cleaning up Docker...$(NC)"
	docker-compose down --rmi all -v
	docker system prune -f
	@echo "$(GREEN)Docker cleanup complete!$(NC)"

# Health Check
health: ## Check backend health
	@echo "$(BLUE)Checking backend health...$(NC)"
	curl -f http://localhost:8000/health || echo "$(RED)Backend not healthy$(NC)"

# Documentation
docs: ## Generate API documentation
	@echo "$(BLUE)Generating API documentation...$(NC)"
	cd backend && python -c "from app.main import app; print(app.openapi())" > openapi.json
	@echo "$(GREEN)API documentation generated!$(NC)"

# Deployment
deploy: ## Deploy to production (placeholder - customize for your deployment)
	@echo "$(YELLOW)Deploy command - customize for your infrastructure$(NC)"
	@echo "Example: docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build"

# All
deploy-all: install test docker-build docker-up
	@echo "$(GREEN)Full deployment complete!$(NC)"
