from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

BACKEND_ROOT = Path(os.getenv("KUL_BACKEND_ROOT", Path(__file__).resolve().parents[2])).resolve()
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal, init_db  # noqa: E402
from app.services.pubmed_client import PubMedClient  # noqa: E402
from app.services.sync_service import LiteratureSyncService  # noqa: E402


def sync_pubmed_publications() -> dict[str, int | None]:
    settings = get_settings()
    init_db()
    db = SessionLocal()
    try:
        client = PubMedClient(
            email=settings.pubmed_email,
            api_key=settings.pubmed_api_key,
            retmax=settings.pubmed_retmax,
        )
        summary = LiteratureSyncService(db, client).sync_all_active_fields()
        return summary.__dict__
    finally:
        db.close()


default_args = {
    "owner": "keep-up-literature",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="keep_up_literature_pubmed_daily_sync",
    description="Fetch current-month PubMed publications for active research fields.",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["pubmed", "literature"],
) as dag:
    PythonOperator(
        task_id="sync_pubmed_publications",
        python_callable=sync_pubmed_publications,
    )
