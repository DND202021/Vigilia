"""Users API endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.deps import DbSession, CurrentUser, require_role
from app.models.user import UserRole
from app.models.audit import AuditAction
from app.services.user_service import UserService, UserError
from app.services.audit_service import AuditService

router = APIRouter()


# Request/Response schemas
class UserCreateRequest(BaseModel):
    """Request schema for creating a user."""

    email: EmailStr
    password: str = Field(min_length=12)
    full_name: str = Field(min_length=1, max_length=200)
    role_id: uuid.UUID | None = None
    agency_id: uuid.UUID | None = None
    badge_number: str | None = None
    phone: str | None = None
    is_verified: bool = False


class UserUpdateRequest(BaseModel):
    """Request schema for updating a user."""

    full_name: str | None = None
    email: EmailStr | None = None
    role_id: uuid.UUID | None = None
    agency_id: uuid.UUID | None = None
    badge_number: str | None = None
    phone: str | None = None
    is_verified: bool | None = None


class PasswordResetRequest(BaseModel):
    """Request schema for password reset."""

    new_password: str = Field(min_length=12)


class RoleResponse(BaseModel):
    """Response schema for role in user response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    color: str | None


class AgencyResponse(BaseModel):
    """Response schema for agency in user response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str


class UserResponse(BaseModel):
    """Response schema for user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    badge_number: str | None
    phone: str | None
    role_name: str
    role_display_name: str
    role: RoleResponse | None
    agency: AgencyResponse | None
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_user(cls, user) -> "UserResponse":
        """Create response from User model."""
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            badge_number=user.badge_number,
            phone=user.phone,
            role_name=user.role_name,
            role_display_name=user.role_display_name,
            role=RoleResponse.model_validate(user.role_obj) if user.role_obj else None,
            agency=AgencyResponse.model_validate(user.agency) if user.agency else None,
            is_active=user.is_active,
            is_verified=user.is_verified,
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )


class UserListResponse(BaseModel):
    """Response schema for user list."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class UserStatsResponse(BaseModel):
    """Response schema for user statistics."""

    total: int
    active: int
    inactive: int
    verified: int
    unverified: int
    by_role: dict[str, int]


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# Endpoints
@router.get("", response_model=UserListResponse)
async def list_users(
    db: DbSession,
    current_user: Annotated[
        Any, Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_ADMIN))
    ],
    agency_id: uuid.UUID | None = Query(None, description="Filter by agency"),
    role_id: uuid.UUID | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    search: str | None = Query(None, description="Search by email, name, or badge"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> UserListResponse:
    """List users with filtering and pagination."""
    user_service = UserService(db)

    # Agency admins can only see users in their agency
    filter_agency = agency_id
    if current_user.role == UserRole.AGENCY_ADMIN and current_user.agency_id:
        filter_agency = current_user.agency_id

    offset = (page - 1) * page_size
    users, total = await user_service.list_users(
        agency_id=filter_agency,
        role_id=role_id,
        is_active=is_active,
        search=search,
        limit=page_size,
        offset=offset,
    )

    return UserListResponse(
        items=[UserResponse.from_user(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    db: DbSession,
    current_user: Annotated[
        Any, Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_ADMIN))
    ],
    agency_id: uuid.UUID | None = Query(None, description="Filter by agency"),
) -> UserStatsResponse:
    """Get user statistics."""
    user_service = UserService(db)

    # Agency admins can only see stats for their agency
    filter_agency = agency_id
    if current_user.role == UserRole.AGENCY_ADMIN and current_user.agency_id:
        filter_agency = current_user.agency_id

    stats = await user_service.get_user_stats(agency_id=filter_agency)
    return UserStatsResponse(**stats)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: DbSession,
    current_user: Annotated[
        Any, Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_ADMIN, UserRole.COMMANDER))
    ],
) -> UserResponse:
    """Get a specific user."""
    user_service = UserService(db)
    user = await user_service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Agency admins can only view users in their agency
    if (
        current_user.role == UserRole.AGENCY_ADMIN
        and current_user.agency_id
        and user.agency_id != current_user.agency_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view users from other agencies",
        )

    return UserResponse.from_user(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_request: UserCreateRequest,
    db: DbSession,
    request: Request,
    current_user: Annotated[
        Any, Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_ADMIN))
    ],
) -> UserResponse:
    """Create a new user."""
    user_service = UserService(db)
    audit_service = AuditService(db)

    # Agency admins can only create users in their agency
    agency_id = user_request.agency_id
    if current_user.role == UserRole.AGENCY_ADMIN and current_user.agency_id:
        agency_id = current_user.agency_id

    try:
        user = await user_service.create_user(
            email=user_request.email,
            password=user_request.password,
            full_name=user_request.full_name,
            role_id=user_request.role_id,
            agency_id=agency_id,
            badge_number=user_request.badge_number,
            phone=user_request.phone,
            is_verified=user_request.is_verified,
        )

        # Log user creation
        await audit_service.log(
            action=AuditAction.USER_CREATED,
            user=current_user,
            entity_type="user",
            entity_id=str(user.id),
            description=f"User created: {user.email}",
            request=request,
            new_values={
                "email": user.email,
                "full_name": user.full_name,
                "role_name": user.role_name,
            },
        )

        return UserResponse.from_user(user)
    except UserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    user_request: UserUpdateRequest,
    db: DbSession,
    request: Request,
    current_user: Annotated[
        Any, Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_ADMIN))
    ],
) -> UserResponse:
    """Update an existing user."""
    user_service = UserService(db)
    audit_service = AuditService(db)

    # Check if user exists and agency access
    existing = await user_service.get_user(user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Capture old values for audit
    old_values = {
        "email": existing.email,
        "full_name": existing.full_name,
        "role_name": existing.role_name,
    }

    if (
        current_user.role == UserRole.AGENCY_ADMIN
        and current_user.agency_id
        and existing.agency_id != current_user.agency_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update users from other agencies",
        )

    # Agency admins cannot change agency_id
    agency_id = user_request.agency_id
    if current_user.role == UserRole.AGENCY_ADMIN:
        agency_id = None

    try:
        user = await user_service.update_user(
            user_id=user_id,
            full_name=user_request.full_name,
            email=user_request.email,
            role_id=user_request.role_id,
            agency_id=agency_id,
            badge_number=user_request.badge_number,
            phone=user_request.phone,
            is_verified=user_request.is_verified,
        )

        # Log user update
        new_values = {
            "email": user.email,
            "full_name": user.full_name,
            "role_name": user.role_name,
        }
        await audit_service.log(
            action=AuditAction.USER_UPDATED,
            user=current_user,
            entity_type="user",
            entity_id=str(user.id),
            description=f"User updated: {user.email}",
            request=request,
            old_values=old_values,
            new_values=new_values,
        )

        return UserResponse.from_user(user)
    except UserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    db: DbSession,
    request: Request,
    current_user: Annotated[
        Any, Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_ADMIN))
    ],
) -> UserResponse:
    """Deactivate a user account."""
    user_service = UserService(db)
    audit_service = AuditService(db)

    # Check permissions
    existing = await user_service.get_user(user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if (
        current_user.role == UserRole.AGENCY_ADMIN
        and current_user.agency_id
        and existing.agency_id != current_user.agency_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate users from other agencies",
        )

    # Prevent self-deactivation
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    try:
        user = await user_service.deactivate_user(user_id)

        # Log deactivation
        await audit_service.log(
            action=AuditAction.USER_UPDATED,
            user=current_user,
            entity_type="user",
            entity_id=str(user.id),
            description=f"User deactivated: {user.email}",
            request=request,
            old_values={"is_active": True},
            new_values={"is_active": False},
        )

        return UserResponse.from_user(user)
    except UserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: uuid.UUID,
    db: DbSession,
    request: Request,
    current_user: Annotated[
        Any, Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_ADMIN))
    ],
) -> UserResponse:
    """Activate a user account."""
    user_service = UserService(db)
    audit_service = AuditService(db)

    existing = await user_service.get_user(user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if (
        current_user.role == UserRole.AGENCY_ADMIN
        and current_user.agency_id
        and existing.agency_id != current_user.agency_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot activate users from other agencies",
        )

    try:
        user = await user_service.activate_user(user_id)

        # Log activation
        await audit_service.log(
            action=AuditAction.USER_UPDATED,
            user=current_user,
            entity_type="user",
            entity_id=str(user.id),
            description=f"User activated: {user.email}",
            request=request,
            old_values={"is_active": False},
            new_values={"is_active": True},
        )

        return UserResponse.from_user(user)
    except UserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{user_id}/verify", response_model=UserResponse)
async def verify_user(
    user_id: uuid.UUID,
    db: DbSession,
    current_user: Annotated[
        Any, Depends(require_role(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_ADMIN))
    ],
) -> UserResponse:
    """Mark a user as verified."""
    user_service = UserService(db)

    existing = await user_service.get_user(user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if (
        current_user.role == UserRole.AGENCY_ADMIN
        and current_user.agency_id
        and existing.agency_id != current_user.agency_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot verify users from other agencies",
        )

    try:
        user = await user_service.verify_user(user_id)
        return UserResponse.from_user(user)
    except UserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
async def reset_password(
    user_id: uuid.UUID,
    password_request: PasswordResetRequest,
    db: DbSession,
    request: Request,
    current_user: Annotated[Any, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> MessageResponse:
    """Reset a user's password (admin only)."""
    user_service = UserService(db)
    audit_service = AuditService(db)

    existing = await user_service.get_user(user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        await user_service.reset_password(user_id, password_request.new_password)

        # Log password reset
        await audit_service.log(
            action=AuditAction.PASSWORD_CHANGED,
            user=current_user,
            entity_type="user",
            entity_id=str(user_id),
            description=f"Password reset by admin for {existing.email}",
            request=request,
            metadata={"reset_by": current_user.email},
        )

        return MessageResponse(message="Password reset successfully")
    except UserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: uuid.UUID,
    db: DbSession,
    request: Request,
    current_user: Annotated[Any, Depends(require_role(UserRole.SYSTEM_ADMIN))],
) -> MessageResponse:
    """Soft delete a user (system admin only)."""
    user_service = UserService(db)
    audit_service = AuditService(db)

    existing = await user_service.get_user(user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    try:
        await user_service.delete_user(user_id)

        # Log user deletion
        await audit_service.log(
            action=AuditAction.USER_DELETED,
            user=current_user,
            entity_type="user",
            entity_id=str(user_id),
            description=f"User deleted: {existing.email}",
            request=request,
            old_values={"email": existing.email, "full_name": existing.full_name},
        )

        return MessageResponse(message="User deleted successfully")
    except UserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
