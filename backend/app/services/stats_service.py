import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.redis import get_redis_client
from app.repositories.complaint_repository import ComplaintRepository

STATS_CACHE_KEY = "stats_cache"
STATS_CACHE_TTL = 30  # 30 seconds TTL


class StatsService:
    """
    Service layer providing Read-Through cached complaint statistics.
    Returns payload and X-Cache status ('HIT' or 'MISS').
    """

    def __init__(self, db: AsyncSession):
        self.repo = ComplaintRepository(db)

    async def get_stats(self) -> tuple[dict[str, Any], str]:
        """
        Retrieves cached stats from Redis or computes them from database.
        Returns:
            Tuple[stats_payload, cache_header_value]
        """
        # Try Redis cache
        try:
            redis_client = await get_redis_client()
            cached_data = await redis_client.get(STATS_CACHE_KEY)
            if cached_data:
                return json.loads(cached_data), "HIT"
        except Exception as e:
            logger.warning(f"Error reading Redis stats_cache: {e}")

        # Cache MISS: compute from PostgreSQL
        stats = await self.repo.get_stats_aggregations()

        # Write to Redis cache with 30s TTL
        try:
            redis_client = await get_redis_client()
            await redis_client.set(STATS_CACHE_KEY, json.dumps(stats), ex=STATS_CACHE_TTL)
        except Exception as e:
            logger.warning(f"Error setting Redis stats_cache: {e}")

        return stats, "MISS"
