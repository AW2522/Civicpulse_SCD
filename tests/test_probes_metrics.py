import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_probe(client: AsyncClient):
    """Test GET /health returns 200 OK without touching dependencies."""
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_readiness_probe_healthy(client: AsyncClient):
    """Test GET /ready returns 200 when dependencies are healthy."""
    res = await client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["dependencies"]["postgres"] == "connected"
    assert data["dependencies"]["redis"] == "connected"


@pytest.mark.asyncio
async def test_readiness_probe_unhealthy(client: AsyncClient):
    """Test GET /ready returns 503 and names failed dependency when postgres/redis fail."""
    from unittest.mock import patch
    with patch("app.routes.probes.check_db_health", return_value=False), \
         patch("app.routes.probes.check_redis_health", return_value=True):
        res = await client.get("/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unhealthy"
        assert "postgres" in data["detail"]
        assert data["dependencies"]["postgres"] == "unreachable"

    with patch("app.routes.probes.check_db_health", return_value=True), \
         patch("app.routes.probes.check_redis_health", return_value=False):
        res = await client.get("/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unhealthy"
        assert "redis" in data["detail"]
        assert data["dependencies"]["redis"] == "unreachable"


@pytest.mark.asyncio
async def test_cors_configuration(client: AsyncClient):
    """Test CORS headers configuration exposes X-Cache and X-Request-ID."""
    res = await client.get(
        "/api/stats",
        headers={"Origin": "http://localhost:5173"}
    )
    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers
    assert "access-control-expose-headers" in res.headers
    exposed = res.headers["access-control-expose-headers"]
    assert "x-cache" in exposed.lower()
    assert "x-request-id" in exposed.lower()


@pytest.mark.asyncio
async def test_provider_meta_endpoint(client: AsyncClient):
    """Test GET /api/meta/providers returns active provider and triage metrics."""
    res = await client.get("/api/meta/providers")
    assert res.status_code == 200
    data = res.json()
    assert "active_provider" in data
    assert "recent_outcomes" in data


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(client: AsyncClient):
    """Test GET /metrics returns 200 with Prometheus text output."""
    res = await client.get("/metrics")
    assert res.status_code == 200
    assert "# HELP" in res.text or "# TYPE" in res.text or "civicpulse" in res.text
