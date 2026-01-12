"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core.deps import DbSession, CurrentUser
from app.services.auth_service import AuthService, AuthenticationError
from app.services.mfa_service import MFAService
from app.models.user import UserRole

router = APIRouter()


# Request schemas
class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str
    mfa_code: str | None = None


class MFASetupRequest(BaseModel):
    """MFA setup confirmation request."""

    secret: str
    code: str = Field(..., min_length=6, max_length=6)


class MFAVerifyRequest(BaseModel):
    """MFA verification request."""

    code: str = Field(..., min_length=6, max_length=6)


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


class MFASetupResponse(BaseModel):
    """MFA setup response with QR code."""

    secret: str
    qr_code: str
    manual_entry_key: str


class LoginResponse(BaseModel):
    """Login response that may require MFA."""

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    mfa_required: bool = False
    mfa_temp_token: str | None = None


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: DbSession) -> LoginResponse:
    """Authenticate user and return tokens.

    If MFA is enabled, returns mfa_required=True with a temporary token.
    The client must then call /auth/mfa/complete with the temp token and code.
    """
    from app.core.security import create_mfa_temp_token

    auth_service = AuthService(db)
    mfa_service = MFAService(db)

    try:
        user = await auth_service.authenticate_user(request.email, request.password)

        # Check if MFA is required
        if user.mfa_enabled and user.mfa_secret:
            if request.mfa_code:
                # Verify MFA code provided with login
                if not await mfa_service.verify_mfa(user, request.mfa_code):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid MFA code",
                    )
                # MFA verified, return tokens
                tokens = await auth_service.create_tokens(user)
                return LoginResponse(
                    access_token=tokens["access_token"],
                    refresh_token=tokens["refresh_token"],
                )
            else:
                # MFA required but no code provided
                temp_token = create_mfa_temp_token(str(user.id))
                return LoginResponse(
                    mfa_required=True,
                    mfa_temp_token=temp_token,
                )

        # No MFA, return tokens directly
        tokens = await auth_service.create_tokens(user)
        return LoginResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
        )
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


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(current_user: CurrentUser, db: DbSession) -> MFASetupResponse:
    """Initialize MFA setup for the current user.

    Returns a secret and QR code for the user to scan with their authenticator app.
    Call /auth/mfa/confirm with the secret and a valid code to enable MFA.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )

    mfa_service = MFAService(db)
    setup_data = await mfa_service.setup_mfa(current_user)

    return MFASetupResponse(**setup_data)


@router.post("/mfa/confirm", response_model=MessageResponse)
async def confirm_mfa_setup(
    request: MFASetupRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Confirm MFA setup by verifying a code from the authenticator app.

    This enables MFA on the user's account.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )

    mfa_service = MFAService(db)
    success = await mfa_service.confirm_mfa_setup(current_user, request.secret, request.code)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    return MessageResponse(message="MFA has been enabled successfully")


@router.post("/mfa/complete", response_model=TokenResponse)
async def complete_mfa_login(
    request: MFAVerifyRequest,
    mfa_temp_token: str,
    db: DbSession,
) -> TokenResponse:
    """Complete login by verifying MFA code.

    Called after login returns mfa_required=True with a temp token.
    """
    from app.core.security import verify_token
    import uuid

    payload = verify_token(mfa_temp_token, token_type="mfa_pending")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    auth_service = AuthService(db)
    mfa_service = MFAService(db)

    user = await auth_service._get_user_by_id(uuid.UUID(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not await mfa_service.verify_mfa(user, request.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    tokens = await auth_service.create_tokens(user)
    return TokenResponse(**tokens)


@router.post("/mfa/disable", response_model=MessageResponse)
async def disable_mfa(
    request: MFAVerifyRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Disable MFA on the current user's account.

    Requires verification with a valid MFA code.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )

    mfa_service = MFAService(db)
    success = await mfa_service.disable_mfa(current_user, request.code)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    return MessageResponse(message="MFA has been disabled")
