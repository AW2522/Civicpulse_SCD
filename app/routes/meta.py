from fastapi import APIRouter
from app.providers.triage_factory import triage_manager

router = APIRouter(prefix="/api/meta", tags=["Metadata"])


@router.get("/providers")
async def get_provider_metadata():
    """
    Returns active triage provider, cache hit rate metrics,
    and last 20 triage outcomes with latency breakdown.
    """
    return triage_manager.get_meta_info()
