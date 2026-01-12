#!/usr/bin/env python3
"""ERIOP Admin Utilities - Manage users and accounts."""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.core.config import settings


async def get_db_session() -> AsyncSession:
    """Create database session."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


async def unlock_user(email: str) -> bool:
    """Unlock a user account."""
    async with await get_db_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ User '{email}' not found")
            return False

        user.locked_until = None
        user.failed_login_attempts = 0
        await db.commit()
        print(f"✅ User '{email}' unlocked successfully")
        return True


async def create_admin_user(email: str, password: str, full_name: str = "System Admin") -> bool:
    """Create a new admin user."""
    async with await get_db_session() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"⚠️  User '{email}' already exists")
            # Update password if requested
            existing.hashed_password = get_password_hash(password)
            existing.is_active = True
            existing.is_verified = True
            existing.locked_until = None
            existing.failed_login_attempts = 0
            await db.commit()
            print(f"✅ User '{email}' password updated and account unlocked")
            return True

        # Create new user
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=UserRole.SYSTEM_ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        print(f"✅ Admin user '{email}' created successfully")
        return True


async def list_users() -> None:
    """List all users."""
    async with await get_db_session() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

        print(f"\n{'Email':<35} {'Role':<15} {'Active':<8} {'Locked':<20}")
        print("-" * 80)
        for user in users:
            locked = user.locked_until or "No"
            print(f"{user.email:<35} {user.role.value:<15} {str(user.is_active):<8} {str(locked):<20}")
        print(f"\nTotal: {len(users)} users")


async def reset_password(email: str, new_password: str) -> bool:
    """Reset a user's password."""
    async with await get_db_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ User '{email}' not found")
            return False

        user.hashed_password = get_password_hash(new_password)
        user.locked_until = None
        user.failed_login_attempts = 0
        await db.commit()
        print(f"✅ Password reset for '{email}'")
        return True


def main():
    parser = argparse.ArgumentParser(description="ERIOP Admin Utilities")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Unlock command
    unlock_parser = subparsers.add_parser("unlock", help="Unlock a user account")
    unlock_parser.add_argument("email", help="User email to unlock")

    # Create admin command
    create_parser = subparsers.add_parser("create-admin", help="Create admin user")
    create_parser.add_argument("email", help="Admin email")
    create_parser.add_argument("password", help="Admin password")
    create_parser.add_argument("--name", default="System Admin", help="Full name")

    # List users command
    subparsers.add_parser("list", help="List all users")

    # Reset password command
    reset_parser = subparsers.add_parser("reset-password", help="Reset user password")
    reset_parser.add_argument("email", help="User email")
    reset_parser.add_argument("password", help="New password")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "unlock":
        asyncio.run(unlock_user(args.email))
    elif args.command == "create-admin":
        asyncio.run(create_admin_user(args.email, args.password, args.name))
    elif args.command == "list":
        asyncio.run(list_users())
    elif args.command == "reset-password":
        asyncio.run(reset_password(args.email, args.password))


if __name__ == "__main__":
    main()
