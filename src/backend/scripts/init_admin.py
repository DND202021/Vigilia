#!/usr/bin/env python3
"""Initialize admin user for ERIOP.

Run this script inside the backend container:
    docker exec -it eriop-backend python scripts/init_admin.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.models.user import User, UserRole
from app.core.security import get_password_hash


# Default admin credentials - override with environment variables
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@vigilia.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin123!@#Strong")
ADMIN_NAME = os.getenv("ADMIN_NAME", "System Administrator")

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://eriop:eriop@postgres:5432/eriop"
)


async def init_admin():
    """Create or update admin user."""
    print(f"🔄 Connecting to database...")

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        user = result.scalar_one_or_none()

        if user:
            print(f"⚠️  User '{ADMIN_EMAIL}' already exists")
            # Update and unlock
            user.hashed_password = get_password_hash(ADMIN_PASSWORD)
            user.is_active = True
            user.is_verified = True
            user.locked_until = None
            user.failed_login_attempts = 0
            user.role = UserRole.SYSTEM_ADMIN
            await db.commit()
            print(f"✅ User '{ADMIN_EMAIL}' updated, unlocked, and password reset")
        else:
            # Create new admin user
            user = User(
                email=ADMIN_EMAIL,
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                full_name=ADMIN_NAME,
                role=UserRole.SYSTEM_ADMIN,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            print(f"✅ Admin user '{ADMIN_EMAIL}' created successfully")

        print(f"\n📧 Email: {ADMIN_EMAIL}")
        print(f"🔑 Password: {ADMIN_PASSWORD}")
        print(f"👤 Role: SYSTEM_ADMIN")

    await engine.dispose()
    print("\n🎉 Admin initialization complete!")


if __name__ == "__main__":
    asyncio.run(init_admin())
