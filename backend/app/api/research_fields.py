from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_pubmed_client
from app.db.session import get_db
from app.repositories.paper_repository import PaperRepository
from app.repositories.research_field_repository import ResearchFieldRepository
from app.schemas.paper import PaperRead, SyncResult
from app.schemas.research_field import ResearchFieldCreate, ResearchFieldRead, ResearchFieldUpdate
from app.services.pubmed_client import PubMedClient
from app.services.sync_service import LiteratureSyncService

router = APIRouter(prefix="/research-fields", tags=["research fields"])


def _with_counts(fields: list, repository: ResearchFieldRepository) -> list[ResearchFieldRead]:
    counts = repository.get_counts()
    response = []
    for field in fields:
        paper_count, unread_count = counts.get(field.id, (0, 0))
        item = ResearchFieldRead.model_validate(field)
        item.paper_count = paper_count
        item.unread_count = unread_count
        response.append(item)
    return response


@router.get("", response_model=list[ResearchFieldRead])
def list_research_fields(db: Session = Depends(get_db)) -> list[ResearchFieldRead]:
    repository = ResearchFieldRepository(db)
    return _with_counts(repository.list(), repository)


@router.post("", response_model=ResearchFieldRead, status_code=status.HTTP_201_CREATED)
def create_research_field(payload: ResearchFieldCreate, db: Session = Depends(get_db)) -> ResearchFieldRead:
    repository = ResearchFieldRepository(db)
    try:
        field = repository.create(payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Research field name already exists.") from exc
    item = ResearchFieldRead.model_validate(field)
    return item


@router.get("/{field_id}", response_model=ResearchFieldRead)
def get_research_field(field_id: int, db: Session = Depends(get_db)) -> ResearchFieldRead:
    repository = ResearchFieldRepository(db)
    field = repository.get(field_id)
    if field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research field not found.")
    return _with_counts([field], repository)[0]


@router.patch("/{field_id}", response_model=ResearchFieldRead)
def update_research_field(
    field_id: int,
    payload: ResearchFieldUpdate,
    db: Session = Depends(get_db),
) -> ResearchFieldRead:
    repository = ResearchFieldRepository(db)
    field = repository.get(field_id)
    if field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research field not found.")
    try:
        updated = repository.update(field, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Research field name already exists.") from exc
    return _with_counts([updated], repository)[0]


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_research_field(field_id: int, db: Session = Depends(get_db)) -> None:
    repository = ResearchFieldRepository(db)
    field = repository.get(field_id)
    if field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research field not found.")
    repository.delete(field)


@router.get("/{field_id}/papers", response_model=list[PaperRead])
def list_papers(field_id: int, db: Session = Depends(get_db)) -> list[PaperRead]:
    fields = ResearchFieldRepository(db)
    if fields.get(field_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research field not found.")
    return PaperRepository(db).list_for_field(field_id)


@router.post("/{field_id}/sync", response_model=SyncResult)
def sync_research_field(
    field_id: int,
    db: Session = Depends(get_db),
    pubmed_client: PubMedClient = Depends(get_pubmed_client),
) -> SyncResult:
    fields = ResearchFieldRepository(db)
    field = fields.get(field_id)
    if field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research field not found.")
    summary = LiteratureSyncService(db, pubmed_client).sync_field(field)
    return SyncResult(**summary.__dict__)
