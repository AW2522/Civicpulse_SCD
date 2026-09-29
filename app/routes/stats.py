from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.stats_service import StatsService

router = APIRouter(prefix="/api/stats", tags=["Stats"])


@router.get("")
async def get_stats(
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregated complaint counts with 30s Read-Through Redis cache.
    Includes 'X-Cache: HIT|MISS' response header.
    """
    service = StatsService(db)
    stats_data, cache_status = await service.get_stats()
    response.headers["X-Cache"] = cache_status
    return stats_data
