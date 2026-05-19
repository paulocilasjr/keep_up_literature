# Keep Up Literature

Keep Up Literature is a local full-stack application for tracking must-read PubMed papers by research field. A user creates research workspaces from keywords or context, the backend turns those inputs into PubMed queries, and a daily Airflow DAG syncs same-day publications into a database.

## What It Does

- Creates research-field workspaces from keywords, context, and an optional description.
- Generates PubMed `Title/Abstract` queries for each workspace.
- Fetches same-day publications from NCBI PubMed E-utilities.
- Stores journal name, publication date, authors, title, abstract, and PubMed link.
- Scores and ranks papers by must-read priority using journal, publication type, keyword match, recency, and metadata completeness.
- Skips papers already saved for the same workspace.
- Remembers deleted papers per workspace so later syncs do not bring them back.
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
cp .env.example .env
# Edit .env with your local path, PubMed email, and optional API key.
set -a
. ./.env
set +a

cd "$KUL_BACKEND_ROOT"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. SQLite creates the database at `KUL_DATABASE_URL` automatically on startup.

Set `KUL_PUBMED_EMAIL` in `.env`. NCBI recommends identifying API clients with an email address; `KUL_PUBMED_API_KEY` is optional.

## Frontend Setup

```bash
set -a
. ./.env
set +a
cd "$KUL_PROJECT_ROOT/frontend"
npm install
cp .env.example .env
npm run dev
```

The UI will be available at `http://localhost:5173`.

## Airflow Setup

Use `.env` for local-only values such as paths, email addresses, and API keys. The file is ignored by git:

```bash
cp .env.example .env
set -a
. ./.env
set +a
```

Edit `.env`:

```bash
KUL_PROJECT_ROOT=/absolute/path/to/keep_up_literature
KUL_BACKEND_ROOT=${KUL_PROJECT_ROOT}/backend
KUL_DATABASE_URL=sqlite:///${KUL_BACKEND_ROOT}/keep_up_literature.db
KUL_PUBMED_EMAIL=your.email@example.com
KUL_PUBMED_API_KEY=
KUL_PUBMED_RETMAX=50
KUL_CORS_ORIGINS='["http://localhost:5173"]'
```

Make the DAG visible to Airflow. A symlink is easiest because it keeps Airflow pointed at this repository version:

```bash
set -a
. ./.env
set +a
mkdir -p "$AIRFLOW_HOME/dags"
ln -sf "$KUL_BACKEND_ROOT/app/airflow_dags/pubmed_daily_sync.py" \
  "$AIRFLOW_HOME/dags/pubmed_daily_sync.py"
```

If you prefer copying the file instead of symlinking it, set `KUL_BACKEND_ROOT` so the copied DAG can import the backend package:

```bash
set -a
. ./.env
set +a
cp backend/app/airflow_dags/pubmed_daily_sync.py "$AIRFLOW_HOME/dags/"
```

Make sure Airflow runs with the backend dependencies available. If your Airflow uses the same Python environment:

```bash
set -a
. ./.env
set +a
cd "$KUL_BACKEND_ROOT"
source .venv/bin/activate
pip install -r requirements.txt
```

The DAG ID is:

```text
keep_up_literature_pubmed_daily_sync
```

It runs daily, checks active research fields, queries PubMed for same-day papers, skips existing or previously deleted records, and inserts new publications.

## Daily Local Runbook

Use this when you want the full project running locally every day.

1. Start the backend API:

```bash
set -a
. ./.env
set +a
cd "$KUL_BACKEND_ROOT"
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

2. Start the frontend in another terminal:

```bash
set -a
. ./.env
set +a
cd "$KUL_PROJECT_ROOT/frontend"
npm install
npm run dev
```

Open `http://localhost:5173`, create research fields, and keep active fields enabled for daily sync.

3. Start Airflow in another terminal if it is not already running:

```bash
export AIRFLOW_HOME="${AIRFLOW_HOME:-$HOME/airflow}"
set -a
. ./.env
set +a
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

If Airflow reports `Broken DAG: .../pubmed_daily_sync.py`, run:

```bash
cd "$KUL_PROJECT_ROOT"
set -a
. ./.env
set +a
airflow dags list-import-errors
```

The most common causes are Airflow not seeing `KUL_BACKEND_ROOT`, or the Airflow Python environment missing the backend dependencies from `backend/requirements.txt`.

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
- `PaperPriorityScorer` owns must-read scoring and explains ranking reasons.
- Repository classes own database access.
- FastAPI routers only handle HTTP concerns.

This keeps the Airflow job, manual API sync, and future CLI tasks using the same business logic.

## Ranking Model

Each newly synced paper receives a `priority_score`, `priority_label`, and `priority_reasons`. The current scoring model is intentionally transparent and uses PubMed metadata already available during sync:

- Journal signal from a curated high-impact journal list.
- Publication type signal for randomized trials, clinical trials, reviews, meta-analyses, and guidelines.
- Keyword density from the research field terms matched in the paper title and abstract.
- Recency of same-day publications.
- Abstract availability as a metadata completeness signal.

The paper table sorts by priority first, then publication date. Citation metadata can be added later if a citation source is connected.
