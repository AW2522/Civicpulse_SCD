import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_complaint_success(client: AsyncClient):
    """Test POST /api/complaints creates, triages, and persists a complaint."""
    payload = {
        "text": "Bhai sahib, massive kachra heap near Commercial Market Saddar.",
        "location": "Commercial Market Saddar, Rawalpindi",
        "reporter_contact": "0300-1122334"
    }
    response = await client.post("/api/complaints", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["category"] == "sanitation"
    assert data["status"] == "open"
    assert data["triaged_by"] == "simulated:default"
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_create_complaint_validation_error(client: AsyncClient):
    """Test POST /api/complaints returns 400 Bad Request on invalid payload (text < 10 chars)."""
    payload = {
        "text": "Too short",
        "location": "Sector G-7/2, Islamabad"
    }
    response = await client.post("/api/complaints", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "validation failed" in data["detail"].lower()
    assert len(data["errors"]) > 0


@pytest.mark.asyncio
async def test_get_complaint_by_id_success(client: AsyncClient):
    """Test GET /api/complaints/{id} returns 200 for existing complaint."""
    # First create a complaint
    payload = {
        "text": "No drinking paani in Sector F-11 since yesterday morning.",
        "location": "Sector F-11/3, Islamabad"
    }
    create_res = await client.post("/api/complaints", json=payload)
    assert create_res.status_code == 201
    complaint_id = create_res.json()["id"]

    # Retrieve by ID
    get_res = await client.get(f"/api/complaints/{complaint_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == complaint_id
    assert get_res.json()["category"] == "water"


@pytest.mark.asyncio
async def test_get_complaint_by_id_not_found(client: AsyncClient):
    """Test GET /api/complaints/{id} returns 404 Not Found for non-existent UUID."""
    random_id = str(uuid.uuid4())
    response = await client.get(f"/api/complaints/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_complaints_filtering_and_pagination(client: AsyncClient):
    """Test GET /api/complaints filters by category and paginates results."""
    # Create two complaints
    await client.post("/api/complaints", json={
        "text": "Huge deep khadda on Murree Road near Chandni Chowk.",
        "location": "Murree Road, Rawalpindi"
    })
    await client.post("/api/complaints", json={
        "text": "Transformer blast near Gali No. 5 Shahdara!",
        "location": "Shahdara, Lahore"
    })

    # List roads complaints
    res = await client.get("/api/complaints?category=roads&page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "roads"
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_state_machine_valid_transitions(client: AsyncClient):
    """Test PATCH /api/complaints/{id}/status for valid transitions (open -> in_progress -> resolved)."""
    # Create complaint (initial status: open)
    create_res = await client.post("/api/complaints", json={
        "text": "Pack of aggressive stray dogs attacking children in park.",
        "location": "Sector I-9/4, Islamabad"
    })
    complaint_id = create_res.json()["id"]

    # open -> in_progress
    res1 = await client.patch(f"/api/complaints/{complaint_id}/status", json={"status": "in_progress"})
    assert res1.status_code == 200
    assert res1.json()["status"] == "in_progress"

    # in_progress -> resolved
    res2 = await client.patch(f"/api/complaints/{complaint_id}/status", json={"status": "resolved"})
    assert res2.status_code == 200
    assert res2.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_state_machine_invalid_transition_returns_409(client: AsyncClient):
    """Test PATCH /api/complaints/{id}/status returns HTTP 409 Conflict on invalid move (resolved -> open)."""
    # Create and resolve complaint
    create_res = await client.post("/api/complaints", json={
        "text": "Dark street lights not working on University Road for 2 km.",
        "location": "University Road, Quetta"
    })
    complaint_id = create_res.json()["id"]

    # Transition to resolved directly
    await client.patch(f"/api/complaints/{complaint_id}/status", json={"status": "resolved"})

    # Attempt illegal transition from resolved -> open
    invalid_res = await client.patch(f"/api/complaints/{complaint_id}/status", json={"status": "open"})
    assert invalid_res.status_code == 409
    data = invalid_res.json()
    assert "invalid state transition" in data["detail"].lower()


@pytest.mark.asyncio
async def test_mandatory_provider_exception_triggers_fallback(client: AsyncClient):
    """
    MANDATORY TEST REQUIREMENT 2:
    Assert that when provider raises an exception (TRIGGER_500 in simulated provider),
    POST returns 201 Created and triaged_by == 'rules:fallback'.
    """
    payload = {
        "text": "TRIGGER_500 Bhai sahib, massive kachra heap near Commercial Market Saddar.",
        "location": "Commercial Market Saddar, Rawalpindi"
    }
    response = await client.post("/api/complaints", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["triaged_by"] == "rules:fallback"
    assert data["category"] == "sanitation"
