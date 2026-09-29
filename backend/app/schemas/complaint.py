import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.complaint import ComplaintCategory, ComplaintPriority, ComplaintStatus


class ComplaintCreate(BaseModel):
    """Input payload for creating a new complaint."""
    text: str = Field(..., min_length=10, max_length=2000, description="Complaint description (10-2000 chars)")
    location: str = Field(..., min_length=3, max_length=200, description="Location of issue (3-200 chars)")
    reporter_contact: str | None = Field(None, max_length=100, description="Optional reporter contact info")


class ComplaintStatusUpdate(BaseModel):
    """Input payload for updating complaint status."""
    status: ComplaintStatus


class ComplaintResponse(BaseModel):
    """API response model for a complaint."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    location: str
    reporter_contact: str | None = None
    category: ComplaintCategory
    priority: ComplaintPriority
    status: ComplaintStatus
    ai_summary: str | None = None
    triaged_by: str
    triage_latency_ms: float
    created_at: datetime
    updated_at: datetime


class PaginatedComplaints(BaseModel):
    """Paginated list response for complaints."""
    items: list[ComplaintResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
