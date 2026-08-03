from collections.abc import Generator

from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
if settings.database_url.startswith("sqlite:///"):
    database_path = Path(settings.database_url.removeprefix("sqlite:///"))
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


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
    table_names = inspector.get_table_names()
    if "papers" not in table_names:
        return
    paper_columns = {column["name"] for column in inspector.get_columns("papers")}
    paper_statements = {
        "publication_types": "ALTER TABLE papers ADD COLUMN publication_types JSON DEFAULT '[]' NOT NULL",
        "priority_score": "ALTER TABLE papers ADD COLUMN priority_score FLOAT DEFAULT 0.0 NOT NULL",
        "priority_label": "ALTER TABLE papers ADD COLUMN priority_label VARCHAR(40) DEFAULT 'Standard' NOT NULL",
        "priority_reasons": "ALTER TABLE papers ADD COLUMN priority_reasons JSON DEFAULT '[]' NOT NULL",
        "is_starred": "ALTER TABLE papers ADD COLUMN is_starred BOOLEAN DEFAULT 0 NOT NULL",
        "is_archived": "ALTER TABLE papers ADD COLUMN is_archived BOOLEAN DEFAULT 0 NOT NULL",
        "notes": "ALTER TABLE papers ADD COLUMN notes TEXT",
        "discarded_at": "ALTER TABLE papers ADD COLUMN discarded_at DATETIME",
        "updated_at": "ALTER TABLE papers ADD COLUMN updated_at DATETIME",
    }
    field_columns = (
        {column["name"] for column in inspector.get_columns("research_fields")}
        if "research_fields" in table_names
        else set()
    )
    field_statements = {
        "last_synced_at": "ALTER TABLE research_fields ADD COLUMN last_synced_at DATETIME",
        "last_sync_status": "ALTER TABLE research_fields ADD COLUMN last_sync_status VARCHAR(40)",
        "last_sync_error": "ALTER TABLE research_fields ADD COLUMN last_sync_error TEXT",
    }
    with engine.begin() as connection:
        for column, statement in paper_statements.items():
            if column not in paper_columns:
                connection.execute(text(statement))
        if "updated_at" not in paper_columns:
            connection.execute(text("UPDATE papers SET updated_at = created_at WHERE updated_at IS NULL"))
        for column, statement in field_statements.items():
            if column not in field_columns:
                connection.execute(text(statement))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_papers_is_starred ON papers (is_starred)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_papers_is_archived ON papers (is_archived)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_papers_discarded_at ON papers (discarded_at)"))
