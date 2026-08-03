from __future__ import annotations

import logging
import threading

from app.core.config import Settings
from app.db.session import SessionLocal
from app.repositories.research_field_repository import ResearchFieldRepository
from app.services.pubmed_client import PubMedClient
from app.services.sync_service import LiteratureSyncService

logger = logging.getLogger(__name__)


class LiteratureSyncScheduler:
    """Small local scheduler that catches up active workspaces while the app runs."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="literature-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run(self) -> None:
        if self._stop_event.wait(self.settings.auto_sync_initial_delay_seconds):
            return
        interval_seconds = self.settings.auto_sync_interval_minutes * 60
        while not self._stop_event.is_set():
            self.sync_now()
            if self._stop_event.wait(interval_seconds):
                return

    def sync_now(self) -> None:
        db = SessionLocal()
        try:
            fields = ResearchFieldRepository(db)
            field_ids = [field.id for field in fields.list_active()]
            client = PubMedClient(
                email=self.settings.pubmed_email,
                api_key=self.settings.pubmed_api_key,
                retmax=self.settings.pubmed_retmax,
            )
            service = LiteratureSyncService(
                db,
                client,
                initial_lookback_days=self.settings.initial_sync_days,
                max_catchup_days=self.settings.max_catchup_days,
            )
            for field_id in field_ids:
                field = fields.get(field_id)
                if field is None:
                    continue
                try:
                    service.sync_field(field)
                except Exception as exc:  # A failing workspace must not block the others.
                    db.rollback()
                    current_field = fields.get(field_id)
                    if current_field is not None:
                        fields.record_sync_failure(current_field, str(exc))
                    logger.exception("Automatic PubMed sync failed for research field %s", field_id)
        finally:
            db.close()
