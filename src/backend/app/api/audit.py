"""Audit log API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission, Permission
from app.models.audit import AuditLog, AuditAction
from app.models.user import User

router = APIRouter()


class AuditLogResponse(BaseModel):
    """Audit log response schema."""

    id: str
    timestamp: datetime
    action: str
    user_id: str | None
    entity_type: str | None
    entity_id: str | None
    description: str | None
    ip_address: str | None
    old_values: dict | None
    new_values: dict | None
    metadata: dict | None


class PaginatedAuditResponse(BaseModel):
    """Paginated audit log response."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


def audit_to_response(log: AuditLog) -> AuditLogResponse:
    """Convert audit log model to response."""
    return AuditLogResponse(
        id=str(log.id),
        timestamp=log.timestamp,
        action=log.action.value,
        user_id=str(log.user_id) if log.user_id else None,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        description=log.description,
        ip_address=log.ip_address,
        old_values=log.old_values,
        new_values=log.new_values,
        metadata=log.extra_data,
    )


@router.get("", response_model=PaginatedAuditResponse)
async def list_audit_logs(
    action: AuditAction | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    user_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_permission(Permission.SYSTEM_AUDIT)),
) -> PaginatedAuditResponse:
    """List audit logs with filters and pagination.

    Requires SYSTEM_AUDIT permission (typically system admins only).
    """
    query = select(AuditLog)

    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    if user_id:
        try:
            user_uuid = uuid.UUID(user_id)
            query = query.where(AuditLog.user_id == user_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format",
            )
    if start_date:
        query = query.where(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.where(AuditLog.timestamp <= end_date)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(
        AuditLog.timestamp.desc()
    )

    result = await db.execute(query)
    logs = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedAuditResponse(
        items=[audit_to_response(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_permission(Permission.SYSTEM_AUDIT)),
) -> AuditLogResponse:
    """Get a specific audit log entry."""
    try:
        log_uuid = uuid.UUID(log_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid log ID format",
        )

    query = select(AuditLog).where(AuditLog.id == log_uuid)
    result = await db.execute(query)
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )

    return audit_to_response(log)


@router.get("/entity/{entity_type}/{entity_id}", response_model=list[AuditLogResponse])
async def get_entity_audit_trail(
    entity_type: str,
    entity_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_permission(Permission.SYSTEM_AUDIT)),
) -> list[AuditLogResponse]:
    """Get complete audit trail for a specific entity."""
    query = (
        select(AuditLog)
        .where(AuditLog.entity_type == entity_type)
        .where(AuditLog.entity_id == entity_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    logs = result.scalars().all()

    return [audit_to_response(log) for log in logs]
