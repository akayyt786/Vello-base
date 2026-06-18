.PHONY: help up down logs migrate test shell build clean

help:
	@echo "OwnFirebase Docker Compose - Convenience Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make up           - Start all services (docker-compose up)"
	@echo "  make down         - Stop all services (docker-compose down)"
	@echo "  make down-v       - Stop services and remove volumes (reset DB)"
	@echo "  make build        - Build Docker images"
	@echo "  make logs         - View logs from all services"
	@echo "  make logs-django  - View logs from django service"
	@echo "  make test         - Run pytest in django container"
	@echo "  make test-ci      - Run pytest with CI profile (dedicated tests service)"
	@echo "  make migrate      - Run Django migrations"
	@echo "  make shell        - Django shell access (python manage.py shell)"
	@echo "  make createsuperuser - Create a superuser"
	@echo "  make clean        - Remove containers, volumes, and orphan services"
	@echo ""

# Start the full stack
up:
	docker-compose up --build

# Start in detached mode
up-d:
	docker-compose up -d --build

# Stop all services
down:
	docker-compose down

# Stop and remove volumes (reset database)
down-v:
	docker-compose down -v

# Build images
build:
	docker-compose build

# View logs
logs:
	docker-compose logs -f

logs-django:
	docker-compose logs -f django

logs-celery:
	docker-compose logs -f celery

logs-redis:
	docker-compose logs -f redis

logs-postgres:
	docker-compose logs -f postgres

# Run migrations
migrate:
	docker-compose exec django python manage.py migrate

# Run migrations with --profile migrations (standalone)
migrate-standalone:
	docker-compose --profile migrations up migrations

# Run pytest
test:
	docker-compose exec django pytest -v

# Run pytest with coverage
test-cov:
	docker-compose exec django pytest --cov=. -v

# Run tests with CI profile (dedicated tests service)
test-ci:
	docker-compose --profile tests up tests

# Django shell
shell:
	docker-compose exec django python manage.py shell

# Create superuser
createsuperuser:
	docker-compose exec django python manage.py createsuperuser

# Clean up
clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

# Health check - verify all services are healthy
health:
	@echo "Checking service health..."
	@docker-compose ps

# Quick start (same as 'make up')
start: up

# Restart services
restart:
	docker-compose restart

# Development flow
dev: up
	@echo "OwnFirebase is running!"
	@echo "Django API: http://localhost:8000"
	@echo "Swagger Docs: http://localhost:8000/api/docs/"
	@echo "Press Ctrl+C to stop"
