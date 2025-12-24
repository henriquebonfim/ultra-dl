.PHONY: up up-d down restart logs logs-backend logs-worker build test test-unit test-integration test-cov bash-backend bash-frontend clean prune

# Development
up:
	docker compose up

up-d:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

# Logs
logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-worker:
	docker compose logs -f celery-worker celery-beat

# Build
build:
	docker compose build

build-no-cache:
	docker compose build --no-cache

# Testing
test:
	docker compose run --rm --entrypoint /bin/bash backend -c "pytest tests/ -v"

test-unit:
	docker compose run --rm --entrypoint /bin/bash backend -c "pytest tests/ -v -m unit"

test-integration:
	docker compose run --rm --entrypoint /bin/bash backend -c "pytest tests/ -v -m integration"

test-cov:
	docker compose run --rm --entrypoint /bin/bash backend -c "pytest tests/ --cov=src --cov-report=html"

# Shell access
bash-backend:
	docker compose run --rm --entrypoint /bin/bash backend

bash-frontend:
	docker compose run --rm --entrypoint /bin/sh frontend

# Cleanup
clean:
	docker compose down -v --remove-orphans
	find . -type d -name "venv" -exec rm -rf {} +
	find . -type d -name ".venv" -exec rm -rf {} +
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".tox" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type d -name "*.egg*" -exec rm -rf {} +
	find . -type d -name "instance" -exec rm -rf {} +
	find . -type d -name "migrations" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type d -name ".expo" -exec rm -rf {} +
	find . -type d -name ".idea" -exec rm -rf {} +
	find . -type d -name "dev-dist" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name ".next" -exec rm -rf {} +
	find . -type d -name ".nuxt" -exec rm -rf {} +
	find . -type d -name ".cache" -exec rm -rf {} +
	find . -type d -name ".parcel-cache" -exec rm -rf {} +
	find . -type d -name ".vite" -exec rm -rf {} +
	find . -type d -name ".terraform" -exec rm -rf {} +
	find . -type f -name ".DS_Store" -exec rm {} +
	find . -type f -name "Thumbs.db" -exec rm {} +
	find . -type f -name "*.log" -exec rm {} +
	find . -type f -name "*.tmp" -exec rm {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type f -name ".coverage" -exec rm {} +

prune:
	docker system prune -f
	docker volume prune -f
