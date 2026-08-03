# Keep Up Literature

Keep Up Literature is a local, durable PubMed reading workspace. It builds focused searches for each research area, catches up on publications missed while the app was stopped, ranks useful papers, and keeps your reading decisions and notes in a persistent SQLite database.

## Start everything with one command

```bash
./keep-up-literature
```

On the first run, the launcher installs missing dependencies and builds the interface. It then starts one local server and automatically opens `http://127.0.0.1:8000` in your browser.

The one process includes:

- The React interface and FastAPI backend.
- A persistent SQLite literature library.
- A lightweight automatic PubMed scheduler.
- Catch-up sync from the last successful date after any shutdown.

Stop it with `Ctrl-C`. Start it again with the same command; workspaces, papers, read/archive state, stars, notes, sync cursors, filters, and unfinished workspace drafts are restored.

Deleting a paper is a durable discard, not destructive data loss. The paper disappears from every normal interface view, search, count, and export, but its complete metadata and annotations remain in SQLite with a discard timestamp. A separate PubMed-ID tombstone ensures later syncs can never import it again.

Useful launcher options:

```bash
./keep-up-literature --no-open     # start without opening a browser
./keep-up-literature --no-sync     # disable background sync for this run
./keep-up-literature --reload      # backend development mode
./keep-up-literature --port 8100   # use another port
```

`make start` is an equivalent entry point.

## Everyday workflow

1. Create a workspace from a name, focused terms, and optional research context.
2. Run **Sync PubMed**. A new workspace collects the last 30 days by default.
3. The app ranks results using journal, study type, keyword density, recency, and metadata quality.
4. Star must-keep papers, mark papers read, add durable research notes, or archive completed items.
5. Search across titles, abstracts, journals, and your notes. Export the current view to CSV when needed.

Active workspaces sync every six hours while the app is running. When it is not running, no background process is required: the next launch uses each workspace's saved cursor to catch up. The catch-up window is bounded to 90 days by default to keep PubMed requests manageable.

## Persistence

The source of truth is SQLite. New installations default to:

```text
data/keep_up_literature.db
```

The database is ignored by Git. SQLite foreign keys, write-ahead logging, and a busy timeout are enabled for safer local operation. Existing installations that set `KUL_DATABASE_URL` continue using that location and are migrated in place without deleting saved rows.

Browser-only working context—the selected workspace, current filters, and a not-yet-submitted workspace draft—is stored in local storage. All research data and paper annotations are stored in SQLite.

Back up the library by copying the database file while the app is stopped. If `-wal` and `-shm` files exist beside it, copy those as well or use SQLite's backup command.

## Configuration

Copy the example and edit local values:

```bash
cp .env.example .env
```

Important settings:

```dotenv
KUL_DATABASE_URL=sqlite:////absolute/path/to/data/keep_up_literature.db
KUL_PUBMED_EMAIL=you@example.com
KUL_PUBMED_API_KEY=
KUL_PUBMED_RETMAX=50
KUL_INITIAL_SYNC_DAYS=30
KUL_MAX_CATCHUP_DAYS=90
KUL_AUTO_SYNC_ENABLED=true
KUL_AUTO_SYNC_INTERVAL_MINUTES=360
KUL_AUTO_SYNC_INITIAL_DELAY_SECONDS=20
```

NCBI recommends identifying E-utilities clients with an email. An API key is optional.

## Architecture

```text
backend/app/
  api/             FastAPI routes
  db/              SQLite engine, sessions, and additive migrations
  models/          Workspaces, papers, and deletion tombstones
  repositories/    Persistent queries and updates
  services/        PubMed, ranking, relevance, catch-up sync, scheduler
frontend/src/       React reading and triage interface
keep-up-literature  One-command production launcher
```

The automatic scheduler and manual API sync use the same `LiteratureSyncService`, so deduplication, deletion tombstones, relevance checks, priority scoring, and cursor updates behave consistently.

## Development and tests

Run the backend tests and production frontend build:

```bash
make test
make build
```

Separate development servers are still available when needed:

```bash
make backend
make frontend
```

The legacy Airflow DAG remains in `backend/app/airflow_dags/pubmed_daily_sync.py` for deployments already using Airflow. Normal local operation does not require Airflow.

## API highlights

- `GET /api/research-fields`
- `POST /api/research-fields`
- `PATCH /api/research-fields/{field_id}`
- `GET /api/research-fields/{field_id}/papers?status=queue&starred=false&search=...`
- `POST /api/research-fields/{field_id}/sync`
- `PATCH /api/papers/{paper_id}`
- `DELETE /api/papers/{paper_id}`
- `GET /docs`
