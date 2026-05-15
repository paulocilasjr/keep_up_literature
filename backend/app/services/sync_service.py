from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models.research_field import ResearchField
from app.repositories.paper_repository import PaperRepository
from app.repositories.research_field_repository import ResearchFieldRepository
from app.services.pubmed_client import PubMedClient


@dataclass
class SyncSummary:
    research_field_id: int | None
    fetched: int = 0
    inserted: int = 0
    skipped_existing: int = 0
    skipped_outside_current_month: int = 0


class LiteratureSyncService:
    def __init__(self, db: Session, pubmed_client: PubMedClient) -> None:
        self.db = db
        self.pubmed_client = pubmed_client
        self.fields = ResearchFieldRepository(db)
        self.papers = PaperRepository(db)

    def sync_all_active_fields(self) -> SyncSummary:
        total = SyncSummary(research_field_id=None)
        for field in self.fields.list_active():
            summary = self.sync_field(field)
            total.fetched += summary.fetched
            total.inserted += summary.inserted
            total.skipped_existing += summary.skipped_existing
            total.skipped_outside_current_month += summary.skipped_outside_current_month
        return total

    def sync_field(self, field: ResearchField, today: date | None = None) -> SyncSummary:
        today = today or date.today()
        articles = self.pubmed_client.search_current_month(field.pubmed_query, today=today)
        summary = SyncSummary(research_field_id=field.id, fetched=len(articles))

        for article in articles:
            if self.papers.exists(field.id, article.pubmed_id):
                summary.skipped_existing += 1
                continue
            if not self.papers.is_in_current_month(article.publication_date, today=today):
                summary.skipped_outside_current_month += 1
                continue
            self.papers.create_from_article(field.id, article)
            summary.inserted += 1

        self.db.commit()
        return summary
