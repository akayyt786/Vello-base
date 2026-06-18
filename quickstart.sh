#!/bin/bash

# Quick start script for Own Firebase Phase 1 MVP

set -e

echo "=========================================="
echo "Own Firebase - Phase 1 MVP Bootstrap"
echo "=========================================="

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "[+] Creating .env from .env.example"
    cp .env.example .env
    echo "    [!] Generated .env. Review and customize as needed."
fi

# Option 1: Docker Compose (recommended)
echo ""
echo "[?] How would you like to run Own Firebase?"
echo "    [1] Docker Compose (recommended) - all services in containers"
echo "    [2] Local setup - requires PostgreSQL 16 + Redis"
read -p "    Choose [1 or 2]: " choice

if [ "$choice" = "1" ]; then
    echo ""
    echo "[+] Starting with Docker Compose..."
    docker-compose build
    docker-compose up -d
    echo ""
    echo "[+] Services starting up. Waiting 5 seconds for database..."
    sleep 5
    echo ""
    echo "[+] Running migrations..."
    docker-compose exec -T django python manage.py migrate
    echo ""
    echo "[+] Creating cache table..."
    docker-compose exec -T django python manage.py createcachetable
    echo ""
    echo "[+] Creating superuser (optional)..."
    docker-compose exec django python manage.py createsuperuser --noinput || true
    echo ""
    echo "=========================================="
    echo "✓ Own Firebase is running!"
    echo "=========================================="
    echo ""
    echo "URLs:"
    echo "  - API:           http://localhost:8000"
    echo "  - Swagger Docs:  http://localhost:8000/api/docs/"
    echo "  - ReDoc:         http://localhost:8000/api/redoc/"
    echo "  - Django Admin:  http://localhost:8000/admin/"
    echo ""
    echo "Services:"
    echo "  - Django:        localhost:8000"
    echo "  - PostgreSQL:    localhost:5432"
    echo "  - Redis:         localhost:6379"
    echo ""
    echo "Next steps:"
    echo "  - View API docs: http://localhost:8000/api/docs/"
    echo "  - Try API: POST /api/v1/auth/register"
    echo "  - Run tests: docker-compose exec django pytest"
    echo "  - Logs: docker-compose logs -f django"
    echo "  - Stop: docker-compose down"

elif [ "$choice" = "2" ]; then
    echo ""
    echo "[!] Local setup requires:"
    echo "    - Python 3.11+"
    echo "    - PostgreSQL 16 (running on localhost:5432)"
    echo "    - Redis (running on localhost:6379)"
    echo ""
    echo "[+] Creating virtual environment..."
    if [ ! -d venv ]; then
        python3.11 -m venv venv || python3 -m venv venv
    fi
    source venv/bin/activate || . venv/Scripts/activate
    echo ""
    echo "[+] Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    echo ""
    echo "[+] Running migrations..."
    python manage.py migrate
    echo ""
    echo "[+] Creating cache table..."
    python manage.py createcachetable
    echo ""
    echo "[+] Starting development server..."
    echo ""
    echo "=========================================="
    echo "✓ Own Firebase is running!"
    echo "=========================================="
    echo ""
    echo "URLs:"
    echo "  - API:           http://localhost:8000"
    echo "  - Swagger Docs:  http://localhost:8000/api/docs/"
    echo "  - ReDoc:         http://localhost:8000/api/redoc/"
    echo "  - Django Admin:  http://localhost:8000/admin/"
    echo ""
    echo "Next steps:"
    echo "  - View API docs: http://localhost:8000/api/docs/"
    echo "  - Create superuser: python manage.py createsuperuser"
    echo "  - Run tests: pytest"
    echo ""
    python manage.py runserver

else
    echo "[!] Invalid choice. Exiting."
    exit 1
fi
