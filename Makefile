.PHONY: help install dev start test clean

help:
	@echo "Available commands:"
	@echo "  make install  - Install dependencies"
	@echo "  make dev      - Start dev server (uvicorn)"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Remove __pycache__ and .pyc files"

install:
	pip install -r requirements.txt

dev:
	python scripts/run_dev.py

test:
	pytest tests/ -v --asyncio-mode=auto

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true