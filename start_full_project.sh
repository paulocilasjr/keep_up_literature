#!/usr/bin/env sh
set -eu

usage() {
  cat <<'USAGE'
Usage: ./start_full_project.sh [--with-airflow|--no-airflow]

Starts the Keep Up Literature backend, frontend, and optionally Airflow.

Options:
  --with-airflow  Start Airflow scheduler and webserver. Fails if Airflow is not installed.
  --no-airflow    Start only the backend and frontend.
  --reload         Run the backend with uvicorn reload enabled.
  -h, --help      Show this help.

By default, Airflow starts automatically when the `airflow` command is available.
USAGE
}

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BACKEND_ROOT="${PROJECT_ROOT}/backend"
FRONTEND_ROOT="${PROJECT_ROOT}/frontend"
START_AIRFLOW="auto"
BACKEND_RELOAD="no"
PIDS=""

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --with-airflow)
      START_AIRFLOW="yes"
      ;;
    --no-airflow)
      START_AIRFLOW="no"
      ;;
    --reload)
      BACKEND_RELOAD="yes"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

cleanup() {
  if [ -n "$PIDS" ]; then
    echo
    echo "Stopping project processes..."
    # shellcheck disable=SC2086
    kill $PIDS 2>/dev/null || true
    wait 2>/dev/null || true
    PIDS=""
  fi
}

trap cleanup INT TERM EXIT

load_env() {
  if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "${PROJECT_ROOT}/.env"
    set +a
  else
    echo "No .env found; using local defaults. Copy .env.example to .env for PubMed settings."
  fi

  export KUL_PROJECT_ROOT="${KUL_PROJECT_ROOT:-$PROJECT_ROOT}"
  export KUL_BACKEND_ROOT="${KUL_BACKEND_ROOT:-$BACKEND_ROOT}"
  export KUL_DATABASE_URL="${KUL_DATABASE_URL:-sqlite:///${KUL_BACKEND_ROOT}/keep_up_literature.db}"
  export KUL_APP_NAME="${KUL_APP_NAME:-Keep Up Literature}"
  export KUL_API_PREFIX="${KUL_API_PREFIX:-/api}"
  export KUL_PUBMED_EMAIL="${KUL_PUBMED_EMAIL:-your.email@example.com}"
  export KUL_PUBMED_API_KEY="${KUL_PUBMED_API_KEY:-}"
  export KUL_PUBMED_RETMAX="${KUL_PUBMED_RETMAX:-50}"
  export KUL_CORS_ORIGINS="${KUL_CORS_ORIGINS:-[\"http://localhost:5173\"]}"
  export VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://localhost:8000}"
  export KUL_BACKEND_HOST="${KUL_BACKEND_HOST:-127.0.0.1}"
  export KUL_BACKEND_PORT="${KUL_BACKEND_PORT:-8000}"
  export KUL_BACKEND_URL_HOST="${KUL_BACKEND_URL_HOST:-localhost}"
  export VITE_HOST="${VITE_HOST:-127.0.0.1}"
  export VITE_PORT="${VITE_PORT:-5173}"
  export VITE_URL_HOST="${VITE_URL_HOST:-localhost}"
}

ensure_backend() {
  cd "$BACKEND_ROOT"

  if [ ! -x ".venv/bin/python" ]; then
    echo "Creating backend virtual environment..."
    python3 -m venv .venv
  fi

  if ! .venv/bin/python -c "import fastapi, uvicorn, sqlalchemy, pydantic, httpx" >/dev/null 2>&1; then
    echo "Installing backend dependencies..."
    .venv/bin/python -m pip install -r requirements.txt
  fi
}

ensure_frontend() {
  cd "$FRONTEND_ROOT"

  if ! command -v npm >/dev/null 2>&1; then
    echo "npm was not found. Install Node.js, then run this script again." >&2
    exit 1
  fi

  if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
  fi

  if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
  fi
}

check_port_free() {
  label="$1"
  host="$2"
  port="$3"

  if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "${label} port ${host}:${port} is already in use." >&2
    echo "Stop that process or set a different port before running this script." >&2
    exit 1
  fi
}

start_process() {
  name="$1"
  shift

  echo "Starting ${name}..."
  "$@" &
  pid="$!"
  PIDS="${PIDS} ${pid}"
  echo "${name} PID: ${pid}"
}

start_backend() {
  reload_arg=""
  if [ "$BACKEND_RELOAD" = "yes" ]; then
    reload_arg=" --reload"
  fi

  start_process "backend API" sh -c "cd '$BACKEND_ROOT' && exec .venv/bin/python -m uvicorn app.main:app --host '$KUL_BACKEND_HOST' --port '$KUL_BACKEND_PORT'${reload_arg}"
}

start_frontend() {
  start_process "frontend UI" sh -c "cd '$FRONTEND_ROOT' && exec npm run dev -- --host '$VITE_HOST' --port '$VITE_PORT'"
}

should_start_airflow() {
  case "$START_AIRFLOW" in
    yes)
      command -v airflow >/dev/null 2>&1 || {
        echo "Airflow was requested, but the airflow command was not found." >&2
        exit 1
      }
      return 0
      ;;
    no)
      return 1
      ;;
    auto)
      command -v airflow >/dev/null 2>&1
      return
      ;;
  esac
}

start_airflow() {
  export AIRFLOW_HOME="${AIRFLOW_HOME:-$HOME/airflow}"
  mkdir -p "$AIRFLOW_HOME/dags"
  ln -sf "$BACKEND_ROOT/app/airflow_dags/pubmed_daily_sync.py" "$AIRFLOW_HOME/dags/pubmed_daily_sync.py"

  start_process "Airflow scheduler" sh -c "exec airflow scheduler"
  start_process "Airflow webserver" sh -c "exec airflow webserver --port 8080"
}

load_env
ensure_backend
ensure_frontend
check_port_free "Backend" "$KUL_BACKEND_HOST" "$KUL_BACKEND_PORT"
check_port_free "Frontend" "$VITE_HOST" "$VITE_PORT"

start_backend
start_frontend

if should_start_airflow; then
  check_port_free "Airflow webserver" "127.0.0.1" "8080"
  start_airflow
else
  echo "Skipping Airflow. Use --with-airflow to require it, or install Airflow for auto-start."
fi

echo
echo "Backend:  http://${KUL_BACKEND_URL_HOST}:${KUL_BACKEND_PORT}"
echo "Frontend: http://${VITE_URL_HOST}:${VITE_PORT}"
if command -v airflow >/dev/null 2>&1 && [ "$START_AIRFLOW" != "no" ]; then
  echo "Airflow:  http://localhost:8080"
fi
echo
echo "Press Ctrl-C to stop all started processes."

wait
