"""Tests for security utilities."""

import pytest
from datetime import timedelta

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_password_hash_is_different_from_plain(self):
        """Password hash should be different from plain password."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert hashed != password

    def test_password_verification_success(self):
        """Correct password should verify successfully."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_password_verification_failure(self):
        """Incorrect password should fail verification."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False

    def test_different_hashes_for_same_password(self):
        """Same password should generate different hashes (salt)."""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2
        # But both should verify
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Tests for JWT token functions."""

    def test_create_access_token(self):
        """Access token should be created successfully."""
        token = create_access_token(subject="user-123")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_claims(self):
        """Access token with additional claims should work."""
        token = create_access_token(
            subject="user-123",
            additional_claims={"role": "admin", "agency_id": "agency-456"},
        )
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"
        assert payload["agency_id"] == "agency-456"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Refresh token should be created successfully."""
        token = create_refresh_token(subject="user-123")
        assert token is not None
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_verify_access_token(self):
        """Valid access token should verify."""
        token = create_access_token(subject="user-123")
        payload = verify_token(token, token_type="access")
        assert payload is not None
        assert payload["sub"] == "user-123"

    def test_verify_refresh_token(self):
        """Valid refresh token should verify."""
        token = create_refresh_token(subject="user-123")
        payload = verify_token(token, token_type="refresh")
        assert payload is not None
        assert payload["sub"] == "user-123"

    def test_wrong_token_type_fails(self):
        """Access token should not verify as refresh token."""
        token = create_access_token(subject="user-123")
        payload = verify_token(token, token_type="refresh")
        assert payload is None

    def test_invalid_token_fails(self):
        """Invalid token should fail verification."""
        payload = verify_token("invalid.token.here", token_type="access")
        assert payload is None

    def test_token_expiration(self):
        """Expired token should fail verification."""
        # Create token that expires immediately
        token = create_access_token(
            subject="user-123",
            expires_delta=timedelta(seconds=-1),
        )
        payload = verify_token(token, token_type="access")
        assert payload is None
