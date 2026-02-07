"""Dependency injection utilities for FastAPI."""

from enum import Enum
from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

import redis.asyncio as aioredis

from app.core.config import settings
from app.models.user import User, UserRole
from app.services.auth_service import AuthService, AuthenticationError


class Permission(str, Enum):
    """Granular permissions for RBAC."""

    # Incident permissions
    INCIDENT_CREATE = "incident:create"
    INCIDENT_READ = "incident:read"
    INCIDENT_UPDATE = "incident:update"
    INCIDENT_DELETE = "incident:delete"
    INCIDENT_ASSIGN = "incident:assign"
    INCIDENT_ESCALATE = "incident:escalate"

    # Alert permissions
    ALERT_READ = "alert:read"
    ALERT_ACKNOWLEDGE = "alert:acknowledge"
    ALERT_DISMISS = "alert:dismiss"
    ALERT_CREATE_INCIDENT = "alert:create_incident"

    # Resource permissions
    RESOURCE_READ = "resource:read"
    RESOURCE_CREATE = "resource:create"
    RESOURCE_UPDATE = "resource:update"
    RESOURCE_DELETE = "resource:delete"
    RESOURCE_ASSIGN = "resource:assign"

    # User management permissions
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE_ROLES = "user:manage_roles"

    # Agency permissions
    AGENCY_READ = "agency:read"
    AGENCY_CREATE = "agency:create"
    AGENCY_UPDATE = "agency:update"
    AGENCY_DELETE = "agency:delete"

    # Dashboard permissions
    DASHBOARD_VIEW = "dashboard:view"
    DASHBOARD_ANALYTICS = "dashboard:analytics"

    # System permissions
    SYSTEM_CONFIG = "system:config"
    SYSTEM_AUDIT = "system:audit"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.SYSTEM_ADMIN: set(Permission),  # All permissions
    UserRole.AGENCY_ADMIN: {
        Permission.INCIDENT_CREATE,
        Permission.INCIDENT_READ,
        Permission.INCIDENT_UPDATE,
        Permission.INCIDENT_ASSIGN,
        Permission.INCIDENT_ESCALATE,
        Permission.ALERT_READ,
        Permission.ALERT_ACKNOWLEDGE,
        Permission.ALERT_DISMISS,
        Permission.ALERT_CREATE_INCIDENT,
        Permission.RESOURCE_READ,
        Permission.RESOURCE_CREATE,
        Permission.RESOURCE_UPDATE,
        Permission.RESOURCE_DELETE,
        Permission.RESOURCE_ASSIGN,
        Permission.USER_READ,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_MANAGE_ROLES,
        Permission.AGENCY_READ,
        Permission.AGENCY_UPDATE,
        Permission.DASHBOARD_VIEW,
        Permission.DASHBOARD_ANALYTICS,
    },
    UserRole.COMMANDER: {
        Permission.INCIDENT_CREATE,
        Permission.INCIDENT_READ,
        Permission.INCIDENT_UPDATE,
        Permission.INCIDENT_ASSIGN,
        Permission.INCIDENT_ESCALATE,
        Permission.ALERT_READ,
        Permission.ALERT_ACKNOWLEDGE,
        Permission.ALERT_DISMISS,
        Permission.ALERT_CREATE_INCIDENT,
        Permission.RESOURCE_READ,
        Permission.RESOURCE_UPDATE,
        Permission.RESOURCE_ASSIGN,
        Permission.USER_READ,
        Permission.DASHBOARD_VIEW,
        Permission.DASHBOARD_ANALYTICS,
    },
    UserRole.DISPATCHER: {
        Permission.INCIDENT_CREATE,
        Permission.INCIDENT_READ,
        Permission.INCIDENT_UPDATE,
        Permission.INCIDENT_ASSIGN,
        Permission.ALERT_READ,
        Permission.ALERT_ACKNOWLEDGE,
        Permission.ALERT_CREATE_INCIDENT,
        Permission.RESOURCE_READ,
        Permission.RESOURCE_ASSIGN,
        Permission.DASHBOARD_VIEW,
    },
    UserRole.FIELD_UNIT_LEADER: {
        Permission.INCIDENT_READ,
        Permission.INCIDENT_UPDATE,
        Permission.ALERT_READ,
        Permission.ALERT_ACKNOWLEDGE,
        Permission.RESOURCE_READ,
        Permission.RESOURCE_UPDATE,
        Permission.DASHBOARD_VIEW,
    },
    UserRole.RESPONDER: {
        Permission.INCIDENT_READ,
        Permission.ALERT_READ,
        Permission.RESOURCE_READ,
        Permission.DASHBOARD_VIEW,
    },
    UserRole.PUBLIC_USER: {
        Permission.INCIDENT_READ,
    },
}

# Database engine and session factory
engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

# Redis client singleton
_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get Redis client singleton. Callable from any context (MQTT handlers, workers, FastAPI)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)
    return _redis_client


# Security scheme
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current authenticated user from JWT token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)

    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_role(*roles: UserRole):
    """Dependency factory for role-based access control."""

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker


def require_permission(*permissions: Permission):
    """Dependency factory for permission-based access control."""

    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        user_permissions = ROLE_PERMISSIONS.get(current_user.role, set())

        for permission in permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value}",
                )
        return current_user

    return permission_checker


def has_permission(user: User, permission: Permission) -> bool:
    """Check if a user has a specific permission."""
    user_permissions = ROLE_PERMISSIONS.get(user.role, set())
    return permission in user_permissions


def has_any_permission(user: User, *permissions: Permission) -> bool:
    """Check if a user has any of the specified permissions."""
    user_permissions = ROLE_PERMISSIONS.get(user.role, set())
    return any(p in user_permissions for p in permissions)


def get_user_permissions(user: User) -> set[Permission]:
    """Get all permissions for a user."""
    return ROLE_PERMISSIONS.get(user.role, set())


# Type aliases for cleaner dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]

# Role-specific type aliases
SystemAdmin = Annotated[User, Depends(require_role(UserRole.SYSTEM_ADMIN))]
AgencyAdmin = Annotated[User, Depends(require_role(UserRole.AGENCY_ADMIN, UserRole.SYSTEM_ADMIN))]
Commander = Annotated[
    User,
    Depends(require_role(UserRole.COMMANDER, UserRole.AGENCY_ADMIN, UserRole.SYSTEM_ADMIN)),
]
Dispatcher = Annotated[
    User,
    Depends(
        require_role(
            UserRole.DISPATCHER,
            UserRole.COMMANDER,
            UserRole.AGENCY_ADMIN,
            UserRole.SYSTEM_ADMIN,
        )
    ),
]

# Permission-specific type aliases
CanCreateIncident = Annotated[User, Depends(require_permission(Permission.INCIDENT_CREATE))]
CanAssignIncident = Annotated[User, Depends(require_permission(Permission.INCIDENT_ASSIGN))]
CanManageResources = Annotated[
    User,
    Depends(require_permission(Permission.RESOURCE_CREATE, Permission.RESOURCE_UPDATE)),
]
CanManageUsers = Annotated[
    User,
    Depends(require_permission(Permission.USER_CREATE, Permission.USER_UPDATE)),
]
