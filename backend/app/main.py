from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api import papers, research_fields
from app.core.config import get_settings
from app.db.session import init_db
from app.services.scheduler import LiteratureSyncScheduler

settings = get_settings()
scheduler = LiteratureSyncScheduler(settings)
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.auto_sync_enabled:
        scheduler.start()
    try:
        yield
    finally:
        scheduler.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "automatic_sync": settings.auto_sync_enabled}


app.include_router(research_fields.router, prefix=settings.api_prefix)
app.include_router(papers.router, prefix=settings.api_prefix)

if (frontend_dist / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="frontend-assets")


@app.get("/", include_in_schema=False)
def frontend_index() -> FileResponse:
    index = frontend_dist / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="Frontend is not built. Run ./keep-up-literature first.")
    return FileResponse(index)


@app.get("/{path:path}", include_in_schema=False)
def frontend_route(path: str) -> FileResponse:
    if path == settings.api_prefix.strip("/") or path.startswith(f"{settings.api_prefix.strip('/')}/"):
        raise HTTPException(status_code=404, detail="API route not found.")
    candidate = (frontend_dist / path).resolve()
    if frontend_dist.resolve() in candidate.parents and candidate.is_file():
        return FileResponse(candidate)
    return frontend_index()
