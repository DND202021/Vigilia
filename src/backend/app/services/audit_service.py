"""Audit logging service for tracking system events."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, AuditAction
from app.models.user import User


class AuditService:
    """Service for creating audit log entries."""

    def __init__(self, db: AsyncSession):
        """Initialize audit service with database session."""
        self.db = db

    async def log(
        self,
        action: AuditAction,
        user: User | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        description: str | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        request: Request | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Create an audit log entry.

        Args:
            action: The type of action being logged
            user: The user performing the action (None for system events)
            entity_type: Type of entity affected (e.g., "incident", "user")
            entity_id: ID of the affected entity
            description: Human-readable description of the action
            old_values: Previous state of entity (for updates)
            new_values: New state of entity (for creates/updates)
            request: FastAPI request object for IP/user agent extraction
            metadata: Additional context data
        """
        # Extract request information
        ip_address = None
        user_agent = None

        if request:
            # Get client IP (handle proxies)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip_address = forwarded.split(",")[0].strip()
            else:
                ip_address = request.client.host if request.client else None

            user_agent = request.headers.get("User-Agent")

        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            action=action,
            user_id=user.id if user else None,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            old_values=old_values,
            new_values=new_values,
            extra_data=metadata,
        )

        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)

        return audit_log

    async def log_login(
        self,
        user: User,
        request: Request | None = None,
        success: bool = True,
    ) -> AuditLog:
        """Log a login attempt."""
        action = AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED
        description = f"User {user.email} {'logged in' if success else 'failed login'}"

        return await self.log(
            action=action,
            user=user if success else None,
            entity_type="user",
            entity_id=str(user.id),
            description=description,
            request=request,
            metadata={"email": user.email, "success": success},
        )

    async def log_entity_change(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        user: User | None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        description: str | None = None,
        request: Request | None = None,
    ) -> AuditLog:
        """Log an entity creation, update, or deletion."""
        return await self.log(
            action=action,
            user=user,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            request=request,
        )

    async def log_permission_denied(
        self,
        user: User,
        resource: str,
        required_permission: str,
        request: Request | None = None,
    ) -> AuditLog:
        """Log a permission denied event."""
        return await self.log(
            action=AuditAction.PERMISSION_DENIED,
            user=user,
            description=f"Permission denied for {resource}",
            request=request,
            metadata={
                "resource": resource,
                "required_permission": required_permission,
            },
        )


# Convenience function for creating audit service with request context
def get_audit_service(db: AsyncSession) -> AuditService:
    """Get an audit service instance."""
    return AuditService(db)
