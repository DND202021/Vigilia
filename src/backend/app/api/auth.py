"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core.deps import DbSession, CurrentUser
from app.services.auth_service import AuthService, AuthenticationError
from app.models.user import UserRole

router = APIRouter()


# Request schemas
class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class RegisterRequest(BaseModel):
    """User registration request schema."""

    email: EmailStr
    password: str = Field(..., min_length=12)
    full_name: str = Field(..., min_length=2, max_length=200)
    badge_number: str | None = None


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""

    current_password: str
    new_password: str = Field(..., min_length=12)


# Response schemas
class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User response schema."""

    id: str
    email: str
    full_name: str
    role: str
    agency_id: str | None = None
    badge_number: str | None = None
    is_verified: bool
    mfa_enabled: bool

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: DbSession) -> TokenResponse:
    """Authenticate user and return tokens."""
    auth_service = AuthService(db)

    try:
        user = await auth_service.authenticate_user(request.email, request.password)
        tokens = await auth_service.create_tokens(user)
        return TokenResponse(**tokens)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: DbSession) -> UserResponse:
    """Register a new user (public users only)."""
    auth_service = AuthService(db)

    try:
        user = await auth_service.create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=UserRole.PUBLIC_USER,
            badge_number=request.badge_number,
        )
        return UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            agency_id=str(user.agency_id) if user.agency_id else None,
            badge_number=user.badge_number,
            is_verified=user.is_verified,
            mfa_enabled=user.mfa_enabled,
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: DbSession) -> TokenResponse:
    """Refresh access token using refresh token."""
    auth_service = AuthService(db)

    try:
        tokens = await auth_service.refresh_access_token(request.refresh_token)
        return TokenResponse(**tokens)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: CurrentUser) -> MessageResponse:
    """Logout user (client should discard tokens)."""
    # In a stateless JWT system, logout is handled client-side
    # For added security, you could maintain a token blacklist in Redis
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: CurrentUser) -> UserResponse:
    """Get current authenticated user."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        agency_id=str(current_user.agency_id) if current_user.agency_id else None,
        badge_number=current_user.badge_number,
        is_verified=current_user.is_verified,
        mfa_enabled=current_user.mfa_enabled,
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Change current user's password."""
    auth_service = AuthService(db)

    try:
        await auth_service.change_password(
            user=current_user,
            current_password=request.current_password,
            new_password=request.new_password,
        )
        return MessageResponse(message="Password changed successfully")
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/mfa/verify", response_model=MessageResponse)
async def verify_mfa(code: str, current_user: CurrentUser) -> MessageResponse:
    """Verify MFA code."""
    # TODO: Implement MFA verification with TOTP
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MFA verification not yet implemented",
    )
