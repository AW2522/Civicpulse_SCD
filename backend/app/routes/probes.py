from fastapi import APIRouter, Response, status

from app.core.database import check_db_health
from app.core.redis import check_redis_health

router = APIRouter(tags=["Probes"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """
    Liveness probe indicating application process is running.
    MUST NOT touch external dependencies (Postgres/Redis)!
    """
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_probe(response: Response):
    """
    Readiness probe validating database and Redis connectivity.
    Returns 503 if any dependency fails.
    """
    db_ok = await check_db_health()
    redis_ok = await check_redis_health()

    if db_ok and redis_ok:
        return {
            "status": "ready",
            "dependencies": {
                "postgres": "connected",
                "redis": "connected"
            }
        }

    failed_deps = []
    if not db_ok:
        failed_deps.append("postgres")
    if not redis_ok:
        failed_deps.append("redis")

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "unhealthy",
        "detail": f"Dependency health checks failed: {', '.join(failed_deps)}",
        "dependencies": {
            "postgres": "connected" if db_ok else "unreachable",
            "redis": "connected" if redis_ok else "unreachable"
        }
    }
