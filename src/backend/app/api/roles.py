"""Roles API endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import DbSession, CurrentUser, require_role
from app.models.user import UserRole
from app.services.role_service import RoleService, RoleError, AVAILABLE_PERMISSIONS

router = APIRouter()


# Request/Response schemas
class RoleCreateRequest(BaseModel):
    """Request schema for creating a role."""

    name: str = Field(min_length=1, max_length=50)
    display_name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    hierarchy_level: int = Field(50, ge=1, le=100)
    color: str | None = Field(None, max_length=20)
    permissions: list[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    """Request schema for updating a role."""

    display_name: str | None = None
    description: str | None = None
    hierarchy_level: int | None = Field(None, ge=1, le=100)
    color: str | None = None
    permissions: list[str] | None = None
    is_active: bool | None = None


class RoleResponse(BaseModel):
    """Response schema for role."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    hierarchy_level: int
    color: str | None
    is_system_role: bool
    is_active: bool
    permissions: list[str]
    user_count: int
    created_at: str
    updated_at: str

    @classmethod
    def from_role(cls, role, user_count: int = 0) -> "RoleResponse":
        """Create response from Role model."""
        return cls(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            hierarchy_level=role.hierarchy_level,
            color=role.color,
            is_system_role=role.is_system_role,
            is_active=role.is_active,
            permissions=role.permissions,
            user_count=user_count,
            created_at=role.created_at.isoformat(),
            updated_at=role.updated_at.isoformat(),
        )


class PermissionResponse(BaseModel):
    """Response schema for permission."""

    key: str
    name: str
    description: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# Endpoints
@router.get("", response_model=list[RoleResponse])
async def list_roles(
    db: DbSession,
    current_user: CurrentUser,
    include_inactive: bool = Query(False, description="Include inactive roles"),
) -> list[RoleResponse]:
    """List all roles."""
    role_service = RoleService(db)
    roles = await role_service.list_roles(include_inactive=include_inactive)

    # Get user counts for each role
    from sqlalchemy import select, func
    from app.models.user import User

    responses = []
    for role in roles:
        count_result = await db.execute(
            select(func.count(User.id)).where(User.role_id == role.id, User.deleted_at == None)
        )
        user_count = count_result.scalar() or 0
        responses.append(RoleResponse.from_role(role, user_count))

    return responses


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    current_user: CurrentUser,
) -> list[PermissionResponse]:
    """List all available permissions."""
    return [PermissionResponse(**p) for p in AVAILABLE_PERMISSIONS]


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> RoleResponse:
    """Get a specific role."""
    role_service = RoleService(db)
    role = await role_service.get_role(role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Get user count
    from sqlalchemy import select, func
    from app.models.user import User

    count_result = await db.execute(
        select(func.count(User.id)).where(User.role_id == role.id, User.deleted_at == None)
    )
    user_count = count_result.scalar() or 0

    return RoleResponse.from_role(role, user_count)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: RoleCreateRequest,
    db: DbSession,
    current_user: Annotated[Any, require_role(UserRole.SYSTEM_ADMIN)],
) -> RoleResponse:
    """Create a new role (system admin only)."""
    role_service = RoleService(db)

    try:
        role = await role_service.create_role(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            hierarchy_level=request.hierarchy_level,
            color=request.color,
            permissions=request.permissions,
        )
        return RoleResponse.from_role(role, 0)
    except RoleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: uuid.UUID,
    request: RoleUpdateRequest,
    db: DbSession,
    current_user: Annotated[Any, require_role(UserRole.SYSTEM_ADMIN)],
) -> RoleResponse:
    """Update an existing role (system admin only)."""
    role_service = RoleService(db)

    try:
        role = await role_service.update_role(
            role_id=role_id,
            display_name=request.display_name,
            description=request.description,
            hierarchy_level=request.hierarchy_level,
            color=request.color,
            permissions=request.permissions,
            is_active=request.is_active,
        )

        # Get user count
        from sqlalchemy import select, func
        from app.models.user import User

        count_result = await db.execute(
            select(func.count(User.id)).where(User.role_id == role.id, User.deleted_at == None)
        )
        user_count = count_result.scalar() or 0

        return RoleResponse.from_role(role, user_count)
    except RoleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{role_id}", response_model=MessageResponse)
async def delete_role(
    role_id: uuid.UUID,
    db: DbSession,
    current_user: Annotated[Any, require_role(UserRole.SYSTEM_ADMIN)],
) -> MessageResponse:
    """Delete a role (system admin only, cannot delete system roles)."""
    role_service = RoleService(db)

    try:
        await role_service.delete_role(role_id)
        return MessageResponse(message="Role deleted successfully")
    except RoleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
