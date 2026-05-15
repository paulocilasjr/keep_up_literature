from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import papers, research_fields
from app.core.config import get_settings
from app.db.session import init_db

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(research_fields.router, prefix=settings.api_prefix)
app.include_router(papers.router, prefix=settings.api_prefix)
