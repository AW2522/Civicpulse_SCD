from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.config import settings


@pytest.mark.asyncio
async def test_rate_limiter_exceeded_returns_429(client: AsyncClient):
    """
    Test that when client IP exceeds RATE_LIMIT_REQUESTS,
    POST /api/complaints returns HTTP 429 with Retry-After header.
    """
    mock_redis = AsyncMock()
    # Simulate current_count > limit (e.g., 6 requests when limit is 5)
    mock_redis.incr.return_value = settings.RATE_LIMIT_REQUESTS + 1
    mock_redis.ttl.return_value = 45

    payload = {
        "text": "Bhai sahib, massive kachra heap near Commercial Market Saddar.",
        "location": "Commercial Market Saddar, Rawalpindi"
    }

    with patch("app.services.rate_limiter.get_redis_client", return_value=mock_redis):
        response = await client.post("/api/complaints", json=payload)

    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "45"
    data = response.json()
    assert "rate limit exceeded" in data["detail"].lower()
