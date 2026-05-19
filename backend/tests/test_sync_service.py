from datetime import date

from app.models.deleted_paper import DeletedPaper
from app.models.research_field import ResearchField
from app.repositories.paper_repository import PaperRepository
from app.services.pubmed_client import PubMedArticle
from app.services.sync_service import LiteratureSyncService


class FakePubMedClient:
    def __init__(self, articles: list[PubMedArticle]) -> None:
        self.articles = articles

    def search_current_day(self, query: str, today: date | None = None) -> list[PubMedArticle]:
        return self.articles

    def search_current_month(self, query: str, today: date | None = None) -> list[PubMedArticle]:
        return self.articles


def test_sync_skips_existing_and_outside_current_day(db_session) -> None:
    field = ResearchField(name="Immunology", keywords=["T cells"], pubmed_query="T cells[Title/Abstract]")
    db_session.add(field)
    db_session.commit()
    db_session.refresh(field)

    article = PubMedArticle(
        pubmed_id="1",
        journal_name="Science",
        publication_date=date(2026, 5, 15),
        author_list=["Doe J"],
        publication_types=["Journal Article"],
        title="A same-day T cells paper",
        abstract="Useful T cells result.",
        link="https://pubmed.ncbi.nlm.nih.gov/1/",
    )
    old_article = PubMedArticle(
        pubmed_id="2",
        journal_name="Nature",
        publication_date=date(2026, 5, 14),
        author_list=["Roe J"],
        publication_types=["Journal Article"],
        title="A previous day T cells paper",
        abstract="T cells.",
        link="https://pubmed.ncbi.nlm.nih.gov/2/",
    )
    service = LiteratureSyncService(db_session, FakePubMedClient([article, old_article]))

    first = service.sync_field(field, today=date(2026, 5, 15))
    second = service.sync_field(field, today=date(2026, 5, 15))

    assert first.inserted == 1
    assert first.skipped_outside_current_day == 1
    assert second.inserted == 0
    assert second.skipped_existing == 1

    saved = db_session.query(field.papers[0].__class__).one()
    assert saved.priority_score > 0
    assert saved.priority_label in {"Medium", "High", "Must read"}


def test_sync_skips_irrelevant_pubmed_matches(db_session) -> None:
    field = ResearchField(
        name="Agents for biomedical research",
        keywords=["Agentic", "LLM agents"],
        pubmed_query='agent*[Title/Abstract] AND LLM[Title/Abstract]',
    )
    db_session.add(field)
    db_session.commit()
    db_session.refresh(field)

    off_topic = PubMedArticle(
        pubmed_id="3",
        journal_name="Oncology",
        publication_date=date(2026, 5, 15),
        author_list=["Doe J"],
        publication_types=["Journal Article"],
        title="Cancer therapeutic agents and artificial intelligence trends",
        abstract="This review discusses therapeutic agents, cancer trials, and artificial intelligence.",
        link="https://pubmed.ncbi.nlm.nih.gov/3/",
    )
    on_topic = PubMedArticle(
        pubmed_id="4",
        journal_name="Science",
        publication_date=date(2026, 5, 15),
        author_list=["Roe J"],
        publication_types=["Journal Article"],
        title="Medical LLM agents for clinical reasoning",
        abstract="Large language model agents support medical clinical reasoning workflows.",
        link="https://pubmed.ncbi.nlm.nih.gov/4/",
    )
    service = LiteratureSyncService(db_session, FakePubMedClient([off_topic, on_topic]))

    summary = service.sync_field(field, today=date(2026, 5, 15))

    assert summary.inserted == 1
    assert summary.skipped_irrelevant == 1


def test_sync_rejects_old_articles_before_relevance_filtering(db_session) -> None:
    field = ResearchField(
        name="Agents for biomedical research",
        keywords=["Agentic", "LLM agents"],
        pubmed_query='agent*[Title/Abstract] AND LLM[Title/Abstract]',
    )
    db_session.add(field)
    db_session.commit()
    db_session.refresh(field)

    old_but_relevant = PubMedArticle(
        pubmed_id="5",
        journal_name="Science",
        publication_date=date(2026, 5, 14),
        author_list=["Doe J"],
        publication_types=["Journal Article"],
        title="Medical LLM agents for clinical reasoning",
        abstract="Large language model agents support medical clinical reasoning workflows.",
        link="https://pubmed.ncbi.nlm.nih.gov/5/",
    )
    service = LiteratureSyncService(db_session, FakePubMedClient([old_but_relevant]))

    summary = service.sync_field(field, today=date(2026, 5, 15))

    assert summary.inserted == 0
    assert summary.skipped_outside_current_day == 1
    assert summary.skipped_irrelevant == 0


def test_sync_skips_previously_deleted_papers(db_session) -> None:
    field = ResearchField(name="Immunology", keywords=["T cells"], pubmed_query="T cells[Title/Abstract]")
    db_session.add(field)
    db_session.commit()
    db_session.refresh(field)

    db_session.add(
        DeletedPaper(
            research_field_id=field.id,
            pubmed_id="6",
            title="Deleted T cells paper",
            publication_date=date(2026, 5, 15),
        )
    )
    db_session.commit()

    deleted_article = PubMedArticle(
        pubmed_id="6",
        journal_name="Science",
        publication_date=date(2026, 5, 15),
        author_list=["Doe J"],
        publication_types=["Journal Article"],
        title="Deleted T cells paper",
        abstract="Useful T cells result.",
        link="https://pubmed.ncbi.nlm.nih.gov/6/",
    )
    service = LiteratureSyncService(db_session, FakePubMedClient([deleted_article]))

    summary = service.sync_field(field, today=date(2026, 5, 15))

    assert summary.inserted == 0
    assert summary.skipped_deleted == 1
    assert field.papers == []


def test_deleting_paper_records_pubmed_id_tombstone(db_session) -> None:
    field = ResearchField(name="Immunology", keywords=["T cells"], pubmed_query="T cells[Title/Abstract]")
    db_session.add(field)
    db_session.commit()
    db_session.refresh(field)

    article = PubMedArticle(
        pubmed_id="7",
        journal_name="Science",
        publication_date=date(2026, 5, 15),
        author_list=["Doe J"],
        publication_types=["Journal Article"],
        title="A same-day T cells paper",
        abstract="Useful T cells result.",
        link="https://pubmed.ncbi.nlm.nih.gov/7/",
    )
    service = LiteratureSyncService(db_session, FakePubMedClient([article]))
    service.sync_field(field, today=date(2026, 5, 15))

    paper = PaperRepository(db_session).list_for_field(field.id)[0]
    PaperRepository(db_session).delete(paper)

    assert PaperRepository(db_session).list_for_field(field.id) == []
    assert PaperRepository(db_session).was_deleted(field.id, "7")
