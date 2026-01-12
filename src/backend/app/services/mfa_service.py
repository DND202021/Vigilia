"""Multi-Factor Authentication service using TOTP."""

import base64
import io
from typing import TYPE_CHECKING

import pyotp
import qrcode
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models.user import User


class MFAService:
    """Service for MFA operations using TOTP."""

    ISSUER = "Vigilia ERIOP"

    def __init__(self, db: AsyncSession):
        """Initialize MFA service with database session."""
        self.db = db

    def generate_secret(self) -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()

    def get_totp_uri(self, user: "User", secret: str) -> str:
        """Generate provisioning URI for authenticator apps."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=user.email, issuer_name=self.ISSUER)

    def generate_qr_code(self, user: "User", secret: str) -> str:
        """Generate QR code as base64 data URL for authenticator apps."""
        uri = self.get_totp_uri(user, secret)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64_data}"

    def verify_code(self, secret: str, code: str) -> bool:
        """Verify a TOTP code against the secret."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    async def setup_mfa(self, user: "User") -> dict:
        """Initialize MFA setup for a user.

        Returns the secret and QR code for the user to scan.
        The MFA is not enabled until confirm_mfa_setup is called.
        """
        secret = self.generate_secret()
        qr_code = self.generate_qr_code(user, secret)

        return {
            "secret": secret,
            "qr_code": qr_code,
            "manual_entry_key": secret,
        }

    async def confirm_mfa_setup(self, user: "User", secret: str, code: str) -> bool:
        """Confirm MFA setup by verifying the first code.

        This enables MFA on the user's account.
        """
        if not self.verify_code(secret, code):
            return False

        user.mfa_secret = secret
        user.mfa_enabled = True
        await self.db.commit()
        return True

    async def disable_mfa(self, user: "User", code: str) -> bool:
        """Disable MFA after verifying current code."""
        if not user.mfa_enabled or not user.mfa_secret:
            return False

        if not self.verify_code(user.mfa_secret, code):
            return False

        user.mfa_enabled = False
        user.mfa_secret = None
        await self.db.commit()
        return True

    async def verify_mfa(self, user: "User", code: str) -> bool:
        """Verify MFA code for an enabled user."""
        if not user.mfa_enabled or not user.mfa_secret:
            return False

        return self.verify_code(user.mfa_secret, code)
