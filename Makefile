.PHONY: start backend frontend test build

start:
	./keep-up-literature

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && PYTHONPATH=. pytest

build:
	cd frontend && VITE_API_BASE_URL= npm run build
