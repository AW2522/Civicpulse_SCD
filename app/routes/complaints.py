import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.complaint import ComplaintCategory, ComplaintPriority, ComplaintStatus
from app.schemas.complaint import ComplaintCreate, ComplaintResponse, ComplaintStatusUpdate, PaginatedComplaints
from app.services.complaint_service import ComplaintService
from app.services.rate_limiter import check_rate_limit

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])


@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    payload: ComplaintCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates, triages, and persists a citizen complaint.
    Enforces Redis rate limiting keyed by client IP.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    is_allowed, retry_after = await check_rate_limit(client_ip)

    if not is_allowed:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum allowed requests reached. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )

    service = ComplaintService(db)
    complaint = await service.create_complaint(payload)
    return complaint


@router.get("/{id}", response_model=ComplaintResponse)
async def get_complaint_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a single complaint by UUID."""
    service = ComplaintService(db)
    return await service.get_complaint_by_id(id)


@router.get("", response_model=PaginatedComplaints)
async def list_complaints(
    category: Optional[ComplaintCategory] = Query(None, description="Filter by category"),
    priority: Optional[ComplaintPriority] = Query(None, description="Filter by priority"),
    status: Optional[ComplaintStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    db: AsyncSession = Depends(get_db),
):
    """Lists complaints with optional filters and pagination."""
    service = ComplaintService(db)
    items, total = await service.list_complaints(
        category=category,
        priority=priority,
        status_filter=status,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedComplaints(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch("/{id}/status", response_model=ComplaintResponse)
async def update_complaint_status(
    id: uuid.UUID,
    payload: ComplaintStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Updates status of a complaint following state machine rules:
    - open -> in_progress, resolved, rejected
    - in_progress -> resolved, rejected
    - terminal states: resolved, rejected (returns 409 on invalid transition)
    """
    service = ComplaintService(db)
    return await service.update_complaint_status(id, payload.status)
