import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_endpoint_returns_aggregations(client: AsyncClient):
    """Test GET /api/stats returns aggregated totals and includes X-Cache header."""
    # Create sample complaints first
    await client.post("/api/complaints", json={
        "text": "Dirty sewage water mixing in main water supply pipe.",
        "location": "Clifton, Karachi"
    })

    res = await client.get("/api/stats")
    assert res.status_code == 200
    assert "X-Cache" in res.headers
    data = res.json()
    assert "total_complaints" in data
    assert "by_status" in data
    assert "by_category" in data
    assert "by_priority" in data
