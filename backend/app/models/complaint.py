import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ComplaintCategory(str, enum.Enum):
    SANITATION = "sanitation"
    WATER = "water"
    ELECTRICITY = "electricity"
    ROADS = "roads"
    PUBLIC_SAFETY = "public_safety"
    OTHER = "other"


class ComplaintPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplaintStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class Complaint(Base):
    """
    Complaint ORM Model for civic issues reported by citizens.
    """
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    reporter_contact: Mapped[str | None] = mapped_column(String(100), nullable=True)

    category: Mapped[ComplaintCategory] = mapped_column(
        Enum(ComplaintCategory, name="complaintcategory", native_enum=False),
        nullable=False,
    )
    priority: Mapped[ComplaintPriority] = mapped_column(
        Enum(ComplaintPriority, name="complaintpriority", native_enum=False),
        nullable=False,
    )
    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus, name="complaintstatus", native_enum=False),
        nullable=False,
        default=ComplaintStatus.OPEN,
    )

    ai_summary: Mapped[str | None] = mapped_column(String(140), nullable=True)
    triaged_by: Mapped[str] = mapped_column(String(50), nullable=False)
    triage_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        # Index 1: Composite index serving GET /api/complaints filtering & GET /api/stats aggregations
        Index("idx_complaints_status_priority", "status", "priority"),
        # Index 2: Single index serving chronological sorting ORDER BY created_at DESC
        Index("idx_complaints_created_at", "created_at"),
    )
