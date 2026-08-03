from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.paper_repository import PaperRepository
from app.schemas.paper import PaperRead, PaperStatusUpdate

router = APIRouter(prefix="/papers", tags=["papers"])


@router.patch("/{paper_id}", response_model=PaperRead)
def update_paper_status(
    paper_id: int,
    payload: PaperStatusUpdate,
    db: Session = Depends(get_db),
) -> PaperRead:
    repository = PaperRepository(db)
    paper = repository.get(paper_id)
    if paper is None or paper.discarded_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found.")
    return repository.update(paper, payload.model_dump(exclude_unset=True))


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(paper_id: int, db: Session = Depends(get_db)) -> None:
    repository = PaperRepository(db)
    paper = repository.get(paper_id)
    if paper is None or paper.discarded_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found.")
    repository.delete(paper)
