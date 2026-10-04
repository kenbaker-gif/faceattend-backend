VENV ?= .venv
PYTHON ?= python3
VENV_BIN := $(VENV)/bin

.PHONY: help setup install run smoke test docker-build docker-run deploy migrate clean

help:
	@echo "FaceAttend Backend - Available Commands"
	@echo "========================================"
	@echo "make setup     - Create .venv and install dependencies"
	@echo "make run       - Run development server from .venv"
	@echo "make smoke     - Check the public local routes"
	@echo "make test      - Run tests"
	@echo "make docker-build - Build the backend image"
	@echo "make docker-run   - Run the backend container"
	@echo "make deploy    - Deploy to production"
	@echo "make migrate   - Show migration SQL"
	@echo "make clean     - Clean pycache and logs"

setup: $(VENV_BIN)/uvicorn

install: setup

$(VENV_BIN)/uvicorn: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/python -m pip install --upgrade pip
	$(VENV_BIN)/python -m pip install -r requirements.txt

run: setup
	$(VENV_BIN)/uvicorn app.main:app --reload --host 0.0.0.0 --port $${PORT:-8080}

smoke: setup
	$(VENV_BIN)/python -c "from fastapi.testclient import TestClient; from app.main import app; c = TestClient(app); assert c.get('/health').json() == {'status': 'ok'}; assert c.get('/').status_code == 200; assert c.get('/dashboard').status_code == 200; print('Local smoke check passed')"

test: setup
	$(VENV_BIN)/python -m pytest tests/ -v

docker-build:
	docker build -t faceattend-backend .

docker-run:
	docker run --rm -p $${PORT:-8080}:$${PORT:-8080} -e PORT=$${PORT:-8080} faceattend-backend

deploy:
	@echo "Deploying to DigitalOcean App Platform..."
	git push origin main

migrate:
	@echo "Run this SQL on your Supabase database:"
	@echo "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMPTZ;"
	@echo "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS last_payment_date TIMESTAMPTZ;"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf logs/*.log 2>/dev/null || true
	@echo "Cleaned cache and logs"
