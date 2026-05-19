from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import deleted_paper, paper, research_field  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()


def _ensure_sqlite_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "papers" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("papers")}
    column_statements = {
        "publication_types": "ALTER TABLE papers ADD COLUMN publication_types JSON DEFAULT '[]' NOT NULL",
        "priority_score": "ALTER TABLE papers ADD COLUMN priority_score FLOAT DEFAULT 0.0 NOT NULL",
        "priority_label": "ALTER TABLE papers ADD COLUMN priority_label VARCHAR(40) DEFAULT 'Standard' NOT NULL",
        "priority_reasons": "ALTER TABLE papers ADD COLUMN priority_reasons JSON DEFAULT '[]' NOT NULL",
    }
    with engine.begin() as connection:
        for column, statement in column_statements.items():
            if column not in existing:
                connection.execute(text(statement))
