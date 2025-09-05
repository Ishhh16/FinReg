# FinReg Application Makefile

.PHONY: help build up down logs clean install test format lint

# Default target
help:
	@echo "FinReg Application Commands:"
	@echo "  build     - Build Docker images"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  logs      - Show application logs"
	@echo "  clean     - Clean up Docker resources"
	@echo "  install   - Install Python dependencies"
	@echo "  test      - Run tests"
	@echo "  format    - Format code"
	@echo "  lint      - Run linting"
	@echo "  reset     - Reset everything (careful!)"

# Docker operations
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker system prune -f

# Development operations
install:
	pip install -r requirements.txt
	pip install pytest black isort mypy

test:
	pytest -v

format:
	black backend/
	isort backend/

lint:
	mypy backend/
	black --check backend/
	isort --check-only backend/

# Database operations
db-shell:
	docker-compose exec db psql -U finreg -d finreg_db

db-backup:
	docker-compose exec db pg_dump -U finreg finreg_db > backup.sql

db-restore:
	docker-compose exec -T db psql -U finreg -d finreg_db < backup.sql

# Administrative
admin-up:
	docker-compose --profile admin up -d

# Reset everything (use with caution)
reset:
	@echo "⚠️  This will delete ALL data. Continue? [y/N]" && read ans && [ $${ans:-N} = y ]
	docker-compose down -v
	docker system prune -af --volumes
	docker-compose up --build -d

# Status check
status:
	@echo "=== FinReg Service Status ==="
	docker-compose ps
	@echo ""
	@echo "=== Health Check ==="
	@curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || echo "API not responding"

# Development server (local)
dev:
	python startup.py