from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from threading import RLock

from sqlalchemy.orm import Session

from app.models.research_field import ResearchField
from app.repositories.paper_repository import PaperRepository
from app.repositories.research_field_repository import ResearchFieldRepository
from app.services.priority_scorer import PaperPriorityScorer
from app.services.pubmed_client import PubMedClient
from app.services.relevance_filter import LiteratureRelevanceFilter

SYNC_LOCK = RLock()


@dataclass
class SyncSummary:
    research_field_id: int | None
    fetched: int = 0
    inserted: int = 0
    skipped_irrelevant: int = 0
    skipped_existing: int = 0
    skipped_deleted: int = 0
    skipped_outside_current_day: int = 0
    sync_from: date | None = None
    sync_to: date | None = None


class LiteratureSyncService:
    def __init__(
        self,
        db: Session,
        pubmed_client: PubMedClient,
        initial_lookback_days: int = 1,
        max_catchup_days: int = 90,
    ) -> None:
        self.db = db
        self.pubmed_client = pubmed_client
        self.scorer = PaperPriorityScorer()
        self.relevance_filter = LiteratureRelevanceFilter()
        self.fields = ResearchFieldRepository(db)
        self.papers = PaperRepository(db)
        self.initial_lookback_days = max(1, initial_lookback_days)
        self.max_catchup_days = max(1, max_catchup_days)

    def sync_all_active_fields(self) -> SyncSummary:
        total = SyncSummary(research_field_id=None)
        for field in self.fields.list_active():
            summary = self.sync_field(field)
            total.fetched += summary.fetched
            total.inserted += summary.inserted
            total.skipped_irrelevant += summary.skipped_irrelevant
            total.skipped_existing += summary.skipped_existing
            total.skipped_deleted += summary.skipped_deleted
            total.skipped_outside_current_day += summary.skipped_outside_current_day
        return total

    def sync_field(
        self,
        field: ResearchField,
        today: date | None = None,
        lookback_days: int | None = None,
    ) -> SyncSummary:
        with SYNC_LOCK:
            return self._sync_field(field, today=today, lookback_days=lookback_days)

    def _sync_field(
        self,
        field: ResearchField,
        today: date | None = None,
        lookback_days: int | None = None,
    ) -> SyncSummary:
        today = today or date.today()
        sync_from = self._sync_start_date(field, today, lookback_days)
        articles = self._search(field.pubmed_query, sync_from, today)
        summary = SyncSummary(
            research_field_id=field.id,
            fetched=len(articles),
            sync_from=sync_from,
            sync_to=today,
        )

        for article in articles:
            if not self.papers.is_in_date_range(article.publication_date, sync_from, today):
                summary.skipped_outside_current_day += 1
                continue
            if self.papers.was_deleted(field.id, article.pubmed_id):
                summary.skipped_deleted += 1
                continue
            if self.papers.exists(field.id, article.pubmed_id):
                summary.skipped_existing += 1
                continue
            if not self.relevance_filter.is_relevant(article, field):
                summary.skipped_irrelevant += 1
                continue
            priority = self.scorer.score(article, field, today=today)
            self.papers.create_from_article(field.id, article, priority)
            summary.inserted += 1

        synced_at = datetime.combine(today, datetime.now(timezone.utc).timetz())
        self.fields.record_sync_success(field, synced_at)
        self.db.commit()
        return summary

    def _sync_start_date(self, field: ResearchField, today: date, lookback_days: int | None) -> date:
        if lookback_days is not None:
            requested_days = max(1, min(lookback_days, self.max_catchup_days))
            return today - timedelta(days=requested_days - 1)
        if field.last_synced_at is not None:
            last_sync_date = field.last_synced_at.date()
            earliest = today - timedelta(days=self.max_catchup_days - 1)
            return max(min(last_sync_date, today), earliest)
        return today - timedelta(days=min(self.initial_lookback_days, self.max_catchup_days) - 1)

    def _search(self, query: str, start: date, end: date) -> list:
        search_date_range = getattr(self.pubmed_client, "search_date_range", None)
        if search_date_range is not None:
            return search_date_range(query, start=start, end=end)
        if start == end:
            return self.pubmed_client.search_current_day(query, today=end)
        return self.pubmed_client.search_current_month(query, today=end)
