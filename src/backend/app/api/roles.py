"""Roles API endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
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


class RoleDuplicateRequest(BaseModel):
    """Request schema for duplicating a role."""

    new_name: str = Field(min_length=1, max_length=50)
    new_display_name: str = Field(min_length=1, max_length=100)


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


class RoleListResponse(BaseModel):
    """Paginated response for role list."""

    items: list[RoleResponse]
    total: int
    page: int
    page_size: int


class RoleStatsResponse(BaseModel):
    """Response schema for role statistics."""

    total: int
    active: int
    inactive: int
    system_roles: int
    custom_roles: int


class PermissionItem(BaseModel):
    """Single permission item."""

    key: str
    name: str
    description: str


class PermissionCategory(BaseModel):
    """Response schema for permission category."""

    category: str
    permissions: list[PermissionItem]


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


async def _get_role_user_count(db: Any, role_id: uuid.UUID) -> int:
    """Get the count of users assigned to a role."""
    from sqlalchemy import select, func
    from app.models.user import User

    count_result = await db.execute(
        select(func.count(User.id)).where(User.role_id == role_id, User.deleted_at == None)
    )
    return count_result.scalar() or 0


# Endpoints
@router.get("", response_model=RoleListResponse)
async def list_roles(
    db: DbSession,
    current_user: CurrentUser,
    include_inactive: bool = Query(False, description="Include inactive roles"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
) -> RoleListResponse:
    """List all roles with pagination."""
    role_service = RoleService(db)
    roles = await role_service.list_roles(include_inactive=include_inactive)

    # Get user counts for each role
    responses = []
    for role in roles:
        user_count = await _get_role_user_count(db, role.id)
        responses.append(RoleResponse.from_role(role, user_count))

    # Apply pagination
    total = len(responses)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = responses[start:end]

    return RoleListResponse(
        items=paginated_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=RoleStatsResponse)
async def get_role_stats(
    db: DbSession,
    current_user: Annotated[Any, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> RoleStatsResponse:
    """Get role statistics (admin only)."""
    role_service = RoleService(db)

    # Get all roles including inactive
    all_roles = await role_service.list_roles(include_inactive=True)

    total = len(all_roles)
    active = sum(1 for r in all_roles if r.is_active)
    inactive = total - active
    system_roles = sum(1 for r in all_roles if r.is_system_role)
    custom_roles = total - system_roles

    return RoleStatsResponse(
        total=total,
        active=active,
        inactive=inactive,
        system_roles=system_roles,
        custom_roles=custom_roles,
    )


@router.get("/permissions", response_model=list[PermissionCategory])
async def list_permissions(
    current_user: CurrentUser,
) -> list[PermissionCategory]:
    """List all available permissions grouped by category."""
    # Group permissions by category (prefix before colon)
    categories: dict[str, list[PermissionItem]] = {}

    for p in AVAILABLE_PERMISSIONS:
        key = p["key"]
        category = key.split(":")[0].title()

        if category not in categories:
            categories[category] = []

        categories[category].append(PermissionItem(
            key=key,
            name=p["name"],
            description=p["description"],
        ))

    return [
        PermissionCategory(category=cat, permissions=perms)
        for cat, perms in categories.items()
    ]


@router.get("/by-name/{name}", response_model=RoleResponse)
async def get_role_by_name(
    name: str,
    db: DbSession,
    current_user: CurrentUser,
) -> RoleResponse:
    """Get a role by its name."""
    role_service = RoleService(db)
    role = await role_service.get_role_by_name(name)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    user_count = await _get_role_user_count(db, role.id)
    return RoleResponse.from_role(role, user_count)


@router.post("/initialize", response_model=MessageResponse)
async def initialize_default_roles(
    db: DbSession,
    current_user: Annotated[Any, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> MessageResponse:
    """Initialize default system roles (admin only)."""
    role_service = RoleService(db)
    await role_service.seed_default_roles()
    return MessageResponse(message="Default roles initialized successfully")


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

    user_count = await _get_role_user_count(db, role.id)
    return RoleResponse.from_role(role, user_count)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: RoleCreateRequest,
    db: DbSession,
    current_user: Annotated[Any, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> RoleResponse:
    """Create a new role (system admin only)."""
    # Validate role name format (lowercase, underscores only)
    import re
    if not re.match(r'^[a-z][a-z0-9_]*$', request.name):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Role name must be lowercase with underscores only, starting with a letter",
        )

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


@router.post("/{role_id}/duplicate", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_role(
    role_id: uuid.UUID,
    request: RoleDuplicateRequest,
    db: DbSession,
    current_user: Annotated[Any, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> RoleResponse:
    """Duplicate an existing role (admin only)."""
    role_service = RoleService(db)

    # Get the source role
    source_role = await role_service.get_role(role_id)
    if not source_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source role not found",
        )

    try:
        # Create new role with same permissions
        new_role = await role_service.create_role(
            name=request.new_name,
            display_name=request.new_display_name,
            description=source_role.description,
            hierarchy_level=source_role.hierarchy_level,
            color=source_role.color,
            permissions=source_role.permissions.copy() if source_role.permissions else [],
            is_system_role=False,
        )
        return RoleResponse.from_role(new_role, 0)
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
    current_user: Annotated[Any, Depends(require_role(UserRole.SYSTEM_ADMIN))],
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

        user_count = await _get_role_user_count(db, role.id)
        return RoleResponse.from_role(role, user_count)
    except RoleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: uuid.UUID,
    db: DbSession,
    current_user: Annotated[Any, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> None:
    """Delete a role (system admin only, cannot delete system roles)."""
    role_service = RoleService(db)

    try:
        await role_service.delete_role(role_id)
    except RoleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
