from datetime import date

from app.models.research_field import ResearchField
from app.services.pubmed_client import PubMedArticle
from app.services.sync_service import LiteratureSyncService


class FakePubMedClient:
    def __init__(self, articles: list[PubMedArticle]) -> None:
        self.articles = articles

    def search_current_month(self, query: str, today: date | None = None) -> list[PubMedArticle]:
        return self.articles


def test_sync_skips_existing_and_outside_current_month(db_session) -> None:
    field = ResearchField(name="Immunology", keywords=["T cells"], pubmed_query="T cells[Title/Abstract]")
    db_session.add(field)
    db_session.commit()
    db_session.refresh(field)

    article = PubMedArticle(
        pubmed_id="1",
        journal_name="Science",
        publication_date=date(2026, 5, 3),
        author_list=["Doe J"],
        title="A current month paper",
        abstract="Useful.",
        link="https://pubmed.ncbi.nlm.nih.gov/1/",
    )
    old_article = PubMedArticle(
        pubmed_id="2",
        journal_name="Nature",
        publication_date=date(2026, 4, 28),
        author_list=["Roe J"],
        title="An older paper",
        abstract=None,
        link="https://pubmed.ncbi.nlm.nih.gov/2/",
    )
    service = LiteratureSyncService(db_session, FakePubMedClient([article, old_article]))

    first = service.sync_field(field, today=date(2026, 5, 15))
    second = service.sync_field(field, today=date(2026, 5, 15))

    assert first.inserted == 1
    assert first.skipped_outside_current_month == 1
    assert second.inserted == 0
    assert second.skipped_existing == 1
