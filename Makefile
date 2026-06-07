.PHONY: help run test deploy migrate clean

help:
	@echo "FaceAttend Backend - Available Commands"
	@echo "========================================"
	@echo "make run       - Run development server"
	@echo "make test      - Run tests"
	@echo "make deploy    - Deploy to production"
	@echo "make migrate   - Show migration SQL"
	@echo "make clean     - Clean pycache and logs"

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

test:
	pytest tests/ -v

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
