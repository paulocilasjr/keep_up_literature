from app.core.config import get_settings
from app.services.pubmed_client import PubMedClient


def get_pubmed_client() -> PubMedClient:
    settings = get_settings()
    return PubMedClient(
        email=settings.pubmed_email,
        api_key=settings.pubmed_api_key,
        retmax=settings.pubmed_retmax,
    )
