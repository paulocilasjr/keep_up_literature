import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Keep Up Literature"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./keep_up_literature.db"
    pubmed_email: str | None = None
    pubmed_api_key: str | None = None
    pubmed_retmax: int = 50
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    return Settings(
        app_name=os.getenv("KUL_APP_NAME", "Keep Up Literature"),
        api_prefix=os.getenv("KUL_API_PREFIX", "/api"),
        database_url=os.getenv("KUL_DATABASE_URL", "sqlite:///./keep_up_literature.db"),
        pubmed_email=os.getenv("KUL_PUBMED_EMAIL") or None,
        pubmed_api_key=os.getenv("KUL_PUBMED_API_KEY") or None,
        pubmed_retmax=int(os.getenv("KUL_PUBMED_RETMAX", "50")),
        cors_origins=_parse_cors_origins(os.getenv("KUL_CORS_ORIGINS")),
    )


def _parse_cors_origins(raw_value: str | None) -> list[str]:
    if not raw_value:
        return ["http://localhost:5173"]
    try:
        parsed = json.loads(raw_value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _load_dotenv() -> None:
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]
    for env_path in candidates:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
