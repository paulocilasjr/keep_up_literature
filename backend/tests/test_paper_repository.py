from datetime import date

from app.models.research_field import ResearchField
from app.repositories.paper_repository import PaperRepository
from app.services.priority_scorer import PriorityScore
from app.services.pubmed_client import PubMedArticle


def test_paper_workflow_state_and_notes_are_persisted(db_session) -> None:
    field = ResearchField(name="Immunology", keywords=["T cells"], pubmed_query="T cells[Title/Abstract]")
    db_session.add(field)
    db_session.commit()
    db_session.refresh(field)
    repository = PaperRepository(db_session)
    paper = repository.create_from_article(
        field.id,
        PubMedArticle(
            pubmed_id="42",
            journal_name="Science",
            publication_date=date(2026, 5, 15),
            author_list=["Doe J"],
            publication_types=["Journal Article"],
            title="T cells persist in a durable niche",
            abstract="T cells remain active.",
            link="https://pubmed.ncbi.nlm.nih.gov/42/",
        ),
        PriorityScore(score=80, label="Must read", reasons=["Relevant"]),
    )
    db_session.commit()

    repository.update(
        paper,
        {"is_read": True, "is_starred": True, "is_archived": True, "notes": "Follow up with the team."},
    )
    db_session.expire_all()
    saved = repository.get(paper.id)

    assert saved is not None
    assert saved.is_read is True
    assert saved.is_starred is True
    assert saved.is_archived is True
    assert saved.notes == "Follow up with the team."
    assert repository.list_for_field(field.id, status="queue") == []
    assert repository.list_for_field(field.id, status="archived") == [saved]
