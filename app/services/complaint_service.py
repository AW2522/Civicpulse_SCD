import uuid
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint import Complaint, ComplaintCategory, ComplaintPriority, ComplaintStatus
from app.schemas.complaint import ComplaintCreate
from app.repositories.complaint_repository import ComplaintRepository
from app.providers.triage_factory import triage_manager
from app.core.redis import get_redis_client
from app.core.logging import logger

# Valid state transition matrix
VALID_TRANSITIONS = {
    ComplaintStatus.OPEN: {ComplaintStatus.IN_PROGRESS, ComplaintStatus.RESOLVED, ComplaintStatus.REJECTED},
    ComplaintStatus.IN_PROGRESS: {ComplaintStatus.RESOLVED, ComplaintStatus.REJECTED},
    ComplaintStatus.RESOLVED: set(),  # Terminal state
    ComplaintStatus.REJECTED: set(),  # Terminal state
}


class ComplaintService:
    """
    Service layer orchestrating complaint creation, status transitions,
    and business rule enforcement.
    """

    def __init__(self, db: AsyncSession):
        self.repo = ComplaintRepository(db)

    async def invalidate_stats_cache(self):
        """Invalidates Redis stats_cache on complaint creation or status update."""
        try:
            redis_client = await get_redis_client()
            await redis_client.delete("stats_cache")
        except Exception as e:
            logger.warning(f"Failed to invalidate stats_cache in Redis: {e}")

    async def create_complaint(self, payload: ComplaintCreate) -> Complaint:
        """
        Creates, triages, and persists a complaint.
        Invalidates stats cache upon success.
        """
        # Step 1: Execute AI Triage (with caching & fallback)
        triage_res, triaged_by, latency_ms = await triage_manager.execute_triage(payload.text, payload.location)

        # Step 2: Construct ORM model
        complaint = Complaint(
            id=uuid.uuid4(),
            text=payload.text,
            location=payload.location,
            reporter_contact=payload.reporter_contact,
            category=triage_res.category,
            priority=triage_res.priority,
            status=ComplaintStatus.OPEN,
            ai_summary=triage_res.summary,
            triaged_by=triaged_by,
            triage_latency_ms=latency_ms,
        )

        # Step 3: Persist in PostgreSQL via Repository
        created_complaint = await self.repo.create(complaint)

        # Step 4: Invalidate stats cache on write
        await self.invalidate_stats_cache()

        return created_complaint

    async def get_complaint_by_id(self, complaint_id: uuid.UUID) -> Complaint:
        """Retrieves complaint by ID or raises HTTP 404."""
        complaint = await self.repo.get_by_id(complaint_id)
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with ID '{complaint_id}' not found."
            )
        return complaint

    async def list_complaints(
        self,
        category: Optional[ComplaintCategory] = None,
        priority: Optional[ComplaintPriority] = None,
        status_filter: Optional[ComplaintStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Complaint], int]:
        """Lists complaints with filters and pagination."""
        return await self.repo.list_complaints(
            category=category,
            priority=priority,
            status=status_filter,
            page=page,
            page_size=page_size
        )

    async def update_complaint_status(
        self, complaint_id: uuid.UUID, new_status: ComplaintStatus
    ) -> Complaint:
        """
        Enforces state machine transitions and updates complaint status.
        Raises HTTP 409 Conflict on invalid transitions.
        """
        complaint = await self.get_complaint_by_id(complaint_id)

        # Check state transition matrix
        current_status = complaint.status
        if new_status not in VALID_TRANSITIONS.get(current_status, set()):
            allowed_str = ", ".join(s.value for s in VALID_TRANSITIONS.get(current_status, set())) or "none (terminal state)"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invalid state transition from '{current_status.value}' to '{new_status.value}'. Allowed transitions from '{current_status.value}': [{allowed_str}]."
            )

        updated = await self.repo.update_status(complaint_id, new_status)
        await self.invalidate_stats_cache()
        return updated
