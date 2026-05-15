# Keep Up Literature

Keep Up Literature is a local full-stack application for tracking must-read PubMed papers by research field. A user creates research workspaces from keywords or context, the backend turns those inputs into PubMed queries, and a daily Airflow DAG syncs current-month publications into a database.

## What It Does

- Creates research-field workspaces from keywords, context, and an optional description.
- Generates PubMed `Title/Abstract` queries for each workspace.
- Fetches current-month publications from NCBI PubMed E-utilities.
- Stores journal name, publication date, authors, title, abstract, and PubMed link.
- Skips papers already saved for the same workspace.
- Lets the user mark papers as read or delete them from the queue.
- Provides a daily Airflow DAG that reuses the same sync service as the API.

## Stack

- Backend: FastAPI, SQLAlchemy, SQLite by default, Pydantic, httpx.
- Frontend: React, Vite, lucide-react.
- Scheduler: Apache Airflow DAG in `backend/app/airflow_dags/pubmed_daily_sync.py`.

## Project Layout

```text
backend/
  app/
    api/             FastAPI routers
    core/            Settings
    db/              SQLAlchemy engine/session
    models/          ORM models
    repositories/    Database access objects
    schemas/         API contracts
    services/        PubMed client, query builder, sync service
    airflow_dags/    Daily Airflow DAG
  tests/
frontend/
  src/
    services/        API client class
    styles/          App CSS
```

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. SQLite creates `backend/keep_up_literature.db` automatically on startup.

Set `KUL_PUBMED_EMAIL` in `backend/.env`. NCBI recommends identifying API clients with an email address; `KUL_PUBMED_API_KEY` is optional.

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The UI will be available at `http://localhost:5173`.

## Airflow Setup

Use an absolute database path so the API and Airflow scheduler always write to the same SQLite file:

```bash
cd /Users/4475918/Projects/personal/keep_up_literature
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```bash
KUL_DATABASE_URL=sqlite:////Users/4475918/Projects/personal/keep_up_literature/backend/keep_up_literature.db
KUL_PUBMED_EMAIL=your.email@example.com
KUL_PUBMED_API_KEY=
KUL_PUBMED_RETMAX=50
KUL_CORS_ORIGINS=["http://localhost:5173"]
```

Make the DAG visible to Airflow. A symlink is easiest because it keeps Airflow pointed at this repository version:

```bash
mkdir -p "$AIRFLOW_HOME/dags"
ln -sf /Users/4475918/Projects/personal/keep_up_literature/backend/app/airflow_dags/pubmed_daily_sync.py \
  "$AIRFLOW_HOME/dags/pubmed_daily_sync.py"
```

If you prefer copying the file instead of symlinking it, set `KUL_BACKEND_ROOT` so the copied DAG can import the backend package:

```bash
export KUL_BACKEND_ROOT=/Users/4475918/Projects/personal/keep_up_literature/backend
cp backend/app/airflow_dags/pubmed_daily_sync.py "$AIRFLOW_HOME/dags/"
```

Make sure Airflow runs with the backend dependencies available. If your Airflow uses the same Python environment:

```bash
cd /Users/4475918/Projects/personal/keep_up_literature/backend
source .venv/bin/activate
pip install -r requirements.txt
export KUL_BACKEND_ROOT=/Users/4475918/Projects/personal/keep_up_literature/backend
export KUL_DATABASE_URL=sqlite:////Users/4475918/Projects/personal/keep_up_literature/backend/keep_up_literature.db
```

The DAG ID is:

```text
keep_up_literature_pubmed_daily_sync
```

It runs daily, checks active research fields, queries PubMed for current-month papers, skips existing records, and inserts new publications.

## Daily Local Runbook

Use this when you want the full project running locally every day.

1. Start the backend API:

```bash
cd /Users/4475918/Projects/personal/keep_up_literature/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

2. Start the frontend in another terminal:

```bash
cd /Users/4475918/Projects/personal/keep_up_literature/frontend
npm install
npm run dev
```

Open `http://localhost:5173`, create research fields, and keep active fields enabled for daily sync.

3. Start Airflow in another terminal if it is not already running:

```bash
export AIRFLOW_HOME="${AIRFLOW_HOME:-$HOME/airflow}"
export KUL_BACKEND_ROOT=/Users/4475918/Projects/personal/keep_up_literature/backend
export KUL_DATABASE_URL=sqlite:////Users/4475918/Projects/personal/keep_up_literature/backend/keep_up_literature.db
airflow scheduler
```

4. Start the Airflow webserver in another terminal if needed:

```bash
export AIRFLOW_HOME="${AIRFLOW_HOME:-$HOME/airflow}"
airflow webserver --port 8080
```

Open `http://localhost:8080`, find `keep_up_literature_pubmed_daily_sync`, unpause it, and confirm the schedule is daily.

5. Test the DAG manually:

```bash
airflow dags test keep_up_literature_pubmed_daily_sync 2026-05-15
```

6. Check the application:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/api/research-fields
```

The backend and Airflow share the same database through `KUL_DATABASE_URL`. The frontend reads from the backend, so new papers added by the daily DAG appear in the relevant research-field workspace.

## API Highlights

- `GET /api/research-fields`
- `POST /api/research-fields`
- `GET /api/research-fields/{field_id}/papers`
- `POST /api/research-fields/{field_id}/sync`
- `PATCH /api/papers/{paper_id}`
- `DELETE /api/papers/{paper_id}`

## Development Notes

The backend is intentionally split into object-oriented layers:

- `PubMedClient` owns PubMed API communication and XML parsing.
- `LiteratureSyncService` owns sync decisions.
- Repository classes own database access.
- FastAPI routers only handle HTTP concerns.

This keeps the Airflow job, manual API sync, and future CLI tasks using the same business logic.
