from typing import Tuple
from app.config import settings
from app.core.redis import get_redis_client
from app.core.logging import logger


async def check_rate_limit(client_ip: str) -> Tuple[bool, int]:
    """
    Fixed-window rate limiter using Redis INCR + EXPIRE.
    Key format: rate_limit:{client_ip}
    Returns:
        Tuple[is_allowed: bool, retry_after_seconds: int]
    """
    try:
        redis_client = await get_redis_client()
        key = f"rate_limit:{client_ip}"
        
        # Atomic increment
        current_count = await redis_client.incr(key)

        # Set expiration on the first request in the window
        if current_count == 1:
            await redis_client.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)

        if current_count > settings.RATE_LIMIT_REQUESTS:
            ttl = await redis_client.ttl(key)
            retry_after = max(1, ttl if ttl > 0 else settings.RATE_LIMIT_WINDOW_SECONDS)
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {current_count}/{settings.RATE_LIMIT_REQUESTS} requests. Retry after {retry_after}s.")
            return False, retry_after

        return True, 0
    except Exception as e:
        logger.error(f"Redis rate limiter error for IP {client_ip}: {e}. Allowing request in fail-open mode.")
        # Fail-open design: if Redis is temporarily unreachable, do not block legitimate user traffic
        return True, 0
