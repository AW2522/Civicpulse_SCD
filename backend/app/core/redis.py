
import redis.asyncio as redis

from app.config import settings
from app.core.logging import logger

redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    """Returns singleton Redis client instance."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


async def check_redis_health() -> bool:
    """Readiness probe Redis health check."""
    try:
        client = await get_redis_client()
        pong = await client.ping()
        return bool(pong)
    except Exception as e:
        logger.error(f"Redis readiness check failed: {e}")
        return False


async def close_redis():
    """Graceful shutdown handler for Redis client."""
    global redis_client
    if redis_client is not None:
        logger.info("Closing Redis connection...")
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed.")
