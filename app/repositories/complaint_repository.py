import uuid
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, func, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.complaint import Complaint, ComplaintCategory, ComplaintPriority, ComplaintStatus


class ComplaintRepository:
    """
    Repository class encapsulating all PostgreSQL database queries for Complaints.
    Enforces strict layer dependency: NO SQL queries outside this file!
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, complaint: Complaint) -> Complaint:
        """Persists a new complaint record."""
        self.db.add(complaint)
        await self.db.commit()
        await self.db.refresh(complaint)
        return complaint

    async def get_by_id(self, complaint_id: uuid.UUID) -> Optional[Complaint]:
        """Retrieves a single complaint by UUID."""
        stmt = select(Complaint).where(Complaint.id == complaint_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_complaints(
        self,
        category: Optional[ComplaintCategory] = None,
        priority: Optional[ComplaintPriority] = None,
        status: Optional[ComplaintStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Complaint], int]:
        """
        Lists complaints with optional filtering by category, priority, status
        and returns paginated items alongside total count.
        Leverages composite index (status, priority) and single index (created_at).
        """
        filters = []
        if category:
            filters.append(Complaint.category == category)
        if priority:
            filters.append(Complaint.priority == priority)
        if status:
            filters.append(Complaint.status == status)

        where_clause = and_(*filters) if filters else True

        # Count total matching records
        count_stmt = select(func.count(Complaint.id)).where(where_clause)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one() or 0

        # Fetch paginated items ordered by created_at DESC
        offset = (page - 1) * page_size
        items_stmt = (
            select(Complaint)
            .where(where_clause)
            .order_by(Complaint.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items_result = await self.db.execute(items_stmt)
        items = list(items_result.scalars().all())

        return items, total

    async def update_status(self, complaint_id: uuid.UUID, new_status: ComplaintStatus) -> Optional[Complaint]:
        """Updates status of a complaint by ID."""
        complaint = await self.get_by_id(complaint_id)
        if not complaint:
            return None

        complaint.status = new_status
        await self.db.commit()
        await self.db.refresh(complaint)
        return complaint

    async def get_stats_aggregations(self) -> Dict[str, Any]:
        """
        Aggregates complaint stats for GET /api/stats:
        - Total count
        - Counts grouped by status
        - Counts grouped by category
        - Counts grouped by priority
        """
        # Total count
        total_stmt = select(func.count(Complaint.id))
        total_res = await self.db.execute(total_stmt)
        total_count = total_res.scalar_one() or 0

        # By status
        status_stmt = select(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status)
        status_res = await self.db.execute(status_stmt)
        by_status = {row[0].value: row[1] for row in status_res.all()}

        # By category
        cat_stmt = select(Complaint.category, func.count(Complaint.id)).group_by(Complaint.category)
        cat_res = await self.db.execute(cat_stmt)
        by_category = {row[0].value: row[1] for row in cat_res.all()}

        # By priority
        prio_stmt = select(Complaint.priority, func.count(Complaint.id)).group_by(Complaint.priority)
        prio_res = await self.db.execute(prio_stmt)
        by_priority = {row[0].value: row[1] for row in prio_res.all()}

        return {
            "total_complaints": total_count,
            "by_status": by_status,
            "by_category": by_category,
            "by_priority": by_priority,
        }
