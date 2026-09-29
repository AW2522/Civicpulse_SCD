from pydantic import BaseModel, Field

from app.models.complaint import ComplaintCategory, ComplaintPriority


class TriageResult(BaseModel):
    """
    Structured outcome of complaint AI/rule-based triage.
    """
    category: ComplaintCategory
    priority: ComplaintPriority
    summary: str = Field(..., max_length=140, description="Concise summary <=140 characters")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
