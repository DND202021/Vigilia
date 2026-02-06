"""Tests for MFAService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.mfa_service import MFAService


@pytest.mark.asyncio
class TestMFAService:
    """Test suite for MFAService."""

    async def test_generate_secret(self, db_session: AsyncSession):
        """Test generating MFA secret."""
        service = MFAService(db_session)

        secret = service.generate_secret()

        assert secret is not None
        assert isinstance(secret, str)
        assert len(secret) > 0

    async def test_generate_qr_code(self, db_session: AsyncSession, test_user: User):
        """Test generating QR code for MFA setup."""
        service = MFAService(db_session)

        secret = service.generate_secret()
        qr_code = service.generate_qr_code(test_user.email, secret, "ERIOP")

        assert qr_code is not None
        assert isinstance(qr_code, str)
        assert len(qr_code) > 0

    async def test_verify_totp_code_valid(self, db_session: AsyncSession):
        """Test verifying valid TOTP code."""
        service = MFAService(db_session)

        secret = service.generate_secret()
        # Generate a valid code
        import pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        is_valid = service.verify_totp_code(secret, valid_code)

        assert is_valid is True

    async def test_verify_totp_code_invalid(self, db_session: AsyncSession):
        """Test verifying invalid TOTP code."""
        service = MFAService(db_session)

        secret = service.generate_secret()
        invalid_code = "000000"

        is_valid = service.verify_totp_code(secret, invalid_code)

        assert is_valid is False

    async def test_enable_mfa_for_user(self, db_session: AsyncSession, test_user: User):
        """Test enabling MFA for a user."""
        service = MFAService(db_session)

        secret = service.generate_secret()
        result = await service.enable_mfa(test_user.id, secret)

        assert result is True

        # Verify user has MFA enabled
        await db_session.refresh(test_user)
        assert test_user.mfa_secret is not None

    async def test_disable_mfa_for_user(self, db_session: AsyncSession, test_user: User):
        """Test disabling MFA for a user."""
        service = MFAService(db_session)

        # First enable MFA
        secret = service.generate_secret()
        await service.enable_mfa(test_user.id, secret)

        # Then disable it
        result = await service.disable_mfa(test_user.id)

        assert result is True

        # Verify user has MFA disabled
        await db_session.refresh(test_user)
        assert test_user.mfa_secret is None

    async def test_verify_user_totp(self, db_session: AsyncSession, test_user: User):
        """Test verifying TOTP code for a user."""
        service = MFAService(db_session)

        # Enable MFA
        secret = service.generate_secret()
        await service.enable_mfa(test_user.id, secret)

        # Generate valid code
        import pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Verify
        is_valid = await service.verify_user_totp(test_user.id, valid_code)

        assert is_valid is True
