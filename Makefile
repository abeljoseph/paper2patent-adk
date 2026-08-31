.PHONY: install test run-cli run-ui run-api docker-build clean

install:
	pip install -r requirements.txt

test:
	PYTHONPATH=. pytest -v tests/

test-cov:
	PYTHONPATH=. pytest --cov=src --cov-report=term-missing tests/

run-cli:
	PYTHONPATH=. python -m src.cli

run-ui:
	PYTHONPATH=. streamlit run src/ui/app.py

run-api:
	PYTHONPATH=. uvicorn src.api:app --reload --port 8000

docker-build:
	docker build -t paper2patent:latest .

docker-run:
	docker compose up --build

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf logs/*.jsonl
