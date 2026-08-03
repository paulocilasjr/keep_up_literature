import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Keep Up Literature"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/keep_up_literature.db"
    pubmed_email: str | None = None
    pubmed_api_key: str | None = None
    pubmed_retmax: int = 50
    initial_sync_days: int = 30
    max_catchup_days: int = 90
    auto_sync_enabled: bool = True
    auto_sync_interval_minutes: int = 360
    auto_sync_initial_delay_seconds: int = 20
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    return Settings(
        app_name=os.getenv("KUL_APP_NAME", "Keep Up Literature"),
        api_prefix=os.getenv("KUL_API_PREFIX", "/api"),
        database_url=_expand_value(os.getenv("KUL_DATABASE_URL", _default_database_url())),
        pubmed_email=os.getenv("KUL_PUBMED_EMAIL") or None,
        pubmed_api_key=os.getenv("KUL_PUBMED_API_KEY") or None,
        pubmed_retmax=int(os.getenv("KUL_PUBMED_RETMAX", "50")),
        initial_sync_days=max(1, int(os.getenv("KUL_INITIAL_SYNC_DAYS", "30"))),
        max_catchup_days=max(1, int(os.getenv("KUL_MAX_CATCHUP_DAYS", "90"))),
        auto_sync_enabled=_parse_bool(os.getenv("KUL_AUTO_SYNC_ENABLED"), default=True),
        auto_sync_interval_minutes=max(5, int(os.getenv("KUL_AUTO_SYNC_INTERVAL_MINUTES", "360"))),
        auto_sync_initial_delay_seconds=max(0, int(os.getenv("KUL_AUTO_SYNC_INITIAL_DELAY_SECONDS", "20"))),
        cors_origins=_parse_cors_origins(os.getenv("KUL_CORS_ORIGINS")),
    )


def _default_database_url() -> str:
    project_root = Path(__file__).resolve().parents[3]
    preferred = project_root / "data" / "keep_up_literature.db"
    legacy = project_root / "backend" / "keep_up_literature.db"
    database_path = legacy if legacy.exists() and not preferred.exists() else preferred
    return f"sqlite:///{database_path}"


def _parse_bool(raw_value: str | None, default: bool = False) -> bool:
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


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
    backend_root = Path(__file__).resolve().parents[2]
    project_root = backend_root.parent
    candidates = [project_root / ".env", backend_root / ".env", Path.cwd() / ".env"]
    for env_path in candidates:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), _expand_value(value.strip().strip('"').strip("'")))


def _expand_value(value: str) -> str:
    return os.path.expanduser(os.path.expandvars(value))
