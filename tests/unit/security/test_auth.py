"""
Tests for croom.security.auth module.
"""

import time
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


class TestPasswordStrength:
    """Tests for PasswordStrength enum."""

    def test_values(self):
        """Test password strength enum values."""
        from croom.security.auth import PasswordStrength

        assert PasswordStrength.VERY_WEAK.value == 0
        assert PasswordStrength.WEAK.value == 1
        assert PasswordStrength.FAIR.value == 2
        assert PasswordStrength.STRONG.value == 3
        assert PasswordStrength.VERY_STRONG.value == 4


class TestPasswordPolicy:
    """Tests for PasswordPolicy dataclass."""

    def test_default_policy(self):
        """Test default password policy."""
        from croom.security.auth import PasswordPolicy

        policy = PasswordPolicy()
        assert policy.min_length >= 8
        assert policy.require_uppercase is True
        assert policy.require_lowercase is True
        assert policy.require_digits is True

    def test_custom_policy(self):
        """Test custom password policy."""
        from croom.security.auth import PasswordPolicy

        policy = PasswordPolicy(
            min_length=12,
            max_length=128,
            require_special=True,
        )
        assert policy.min_length == 12
        assert policy.require_special is True


class TestCommonPasswords:
    """Tests for common password rejection."""

    def test_common_passwords_list(self):
        """Test common passwords list exists."""
        from croom.security.auth import COMMON_PASSWORDS

        assert "password" in COMMON_PASSWORDS
        assert "123456" in COMMON_PASSWORDS
        assert "admin" in COMMON_PASSWORDS


class TestPasswordValidator:
    """Tests for password validation."""

    def test_validate_short_password(self):
        """Test validation rejects short passwords."""
        from croom.security.auth import PasswordPolicy, PasswordValidator

        policy = PasswordPolicy(min_length=8)
        validator = PasswordValidator(policy)

        result = validator.validate("short")
        assert result.is_valid is False

    def test_validate_strong_password(self):
        """Test validation accepts strong passwords."""
        from croom.security.auth import PasswordPolicy, PasswordValidator

        policy = PasswordPolicy()
        validator = PasswordValidator(policy)

        result = validator.validate("Str0ng!P@ssword123")
        assert result.is_valid is True

    def test_validate_common_password(self):
        """Test validation rejects common passwords."""
        from croom.security.auth import PasswordPolicy, PasswordValidator

        policy = PasswordPolicy()
        validator = PasswordValidator(policy)

        result = validator.validate("password123")
        assert result.is_valid is False


class TestTOTPGenerator:
    """Tests for TOTP (2FA) generation."""

    def test_generate_secret(self):
        """Test generating TOTP secret."""
        from croom.security.auth import TOTPGenerator

        generator = TOTPGenerator()
        secret = generator.generate_secret()

        assert secret is not None
        assert len(secret) == 32  # Base32 encoded

    def test_generate_totp(self):
        """Test generating TOTP code."""
        from croom.security.auth import TOTPGenerator

        generator = TOTPGenerator()
        secret = generator.generate_secret()
        code = generator.generate_totp(secret)

        assert code is not None
        assert len(code) == 6
        assert code.isdigit()

    def test_verify_totp(self):
        """Test verifying TOTP code."""
        from croom.security.auth import TOTPGenerator

        generator = TOTPGenerator()
        secret = generator.generate_secret()
        code = generator.generate_totp(secret)

        is_valid = generator.verify_totp(secret, code)
        assert is_valid is True

    def test_verify_invalid_totp(self):
        """Test verifying invalid TOTP code."""
        from croom.security.auth import TOTPGenerator

        generator = TOTPGenerator()
        secret = generator.generate_secret()

        is_valid = generator.verify_totp(secret, "000000")
        assert is_valid is False
