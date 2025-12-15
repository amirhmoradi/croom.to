"""
Authentication services for PiMeet.

Provides password policy, MFA, and session management.
"""

import base64
import hashlib
import hmac
import logging
import os
import re
import secrets
import struct
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
import json

logger = logging.getLogger(__name__)


# Common passwords to reject (truncated list - full list would be larger)
COMMON_PASSWORDS = {
    "password", "123456", "12345678", "qwerty", "abc123", "monkey", "1234567",
    "letmein", "trustno1", "dragon", "baseball", "iloveyou", "master", "sunshine",
    "ashley", "bailey", "passw0rd", "shadow", "123123", "654321", "superman",
    "qazwsx", "michael", "football", "password1", "password123", "welcome",
    "admin", "administrator", "root", "pimeet", "conference", "meeting",
}


class PasswordStrength(Enum):
    """Password strength levels."""
    VERY_WEAK = 0
    WEAK = 1
    FAIR = 2
    STRONG = 3
    VERY_STRONG = 4


@dataclass
class PasswordPolicy:
    """
    Password policy configuration.

    Enforces security requirements for passwords.
    """
    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    special_chars: str = "!@#$%^&*()_+-=[]{}|;:',.<>?/`~"
    min_unique_chars: int = 8
    reject_common: bool = True
    reject_user_info: bool = True
    max_repeated_chars: int = 3
    password_history: int = 5  # Number of previous passwords to check
    min_age_hours: int = 1  # Minimum time before password can be changed
    max_age_days: int = 90  # Maximum password age

    def validate(
        self,
        password: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        previous_hashes: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate a password against the policy.

        Args:
            password: Password to validate
            username: Username (for similarity check)
            email: Email (for similarity check)
            previous_hashes: Hashes of previous passwords

        Returns:
            Tuple of (is_valid, list of violation messages)
        """
        violations = []

        # Length checks
        if len(password) < self.min_length:
            violations.append(f"Password must be at least {self.min_length} characters")
        if len(password) > self.max_length:
            violations.append(f"Password must be at most {self.max_length} characters")

        # Character class checks
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            violations.append("Password must contain uppercase letter")
        if self.require_lowercase and not re.search(r'[a-z]', password):
            violations.append("Password must contain lowercase letter")
        if self.require_digit and not re.search(r'\d', password):
            violations.append("Password must contain digit")
        if self.require_special and not any(c in self.special_chars for c in password):
            violations.append("Password must contain special character")

        # Unique characters
        if len(set(password)) < self.min_unique_chars:
            violations.append(f"Password must have at least {self.min_unique_chars} unique characters")

        # Repeated characters
        for i in range(len(password) - self.max_repeated_chars):
            if len(set(password[i:i + self.max_repeated_chars + 1])) == 1:
                violations.append(f"Password cannot have more than {self.max_repeated_chars} repeated characters")
                break

        # Common password check
        if self.reject_common and password.lower() in COMMON_PASSWORDS:
            violations.append("Password is too common")

        # User info check
        if self.reject_user_info:
            if username and username.lower() in password.lower():
                violations.append("Password cannot contain username")
            if email:
                email_local = email.split('@')[0].lower()
                if email_local in password.lower():
                    violations.append("Password cannot contain email address")

        # Previous password check
        if previous_hashes and self.password_history > 0:
            current_hash = self._hash_password(password)
            if current_hash in previous_hashes[:self.password_history]:
                violations.append(f"Cannot reuse last {self.password_history} passwords")

        return len(violations) == 0, violations

    def _hash_password(self, password: str) -> str:
        """Hash password for history comparison."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def get_strength(self, password: str) -> PasswordStrength:
        """
        Calculate password strength.

        Args:
            password: Password to evaluate

        Returns:
            PasswordStrength level
        """
        score = 0

        # Length scoring
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
        if len(password) >= 20:
            score += 1

        # Character class scoring
        if re.search(r'[a-z]', password):
            score += 1
        if re.search(r'[A-Z]', password):
            score += 1
        if re.search(r'\d', password):
            score += 1
        if re.search(r'[^a-zA-Z\d]', password):
            score += 1

        # Unique characters
        if len(set(password)) >= 8:
            score += 1

        # Deductions
        if password.lower() in COMMON_PASSWORDS:
            score -= 3

        # Sequential patterns
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):
            score -= 1
        if re.search(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):
            score -= 1

        # Map to strength
        if score <= 2:
            return PasswordStrength.VERY_WEAK
        elif score <= 4:
            return PasswordStrength.WEAK
        elif score <= 6:
            return PasswordStrength.FAIR
        elif score <= 8:
            return PasswordStrength.STRONG
        else:
            return PasswordStrength.VERY_STRONG


class MFAType(Enum):
    """MFA method types."""
    TOTP = "totp"
    WEBAUTHN = "webauthn"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODE = "backup_code"


@dataclass
class MFASetup:
    """MFA setup information."""
    mfa_type: MFAType
    secret: Optional[str] = None  # TOTP secret
    credential_id: Optional[str] = None  # WebAuthn credential ID
    phone_number: Optional[str] = None  # SMS number
    email: Optional[str] = None  # Email address
    backup_codes: Optional[List[str]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    is_primary: bool = False


class MFAProvider(ABC):
    """Abstract base class for MFA providers."""

    @abstractmethod
    def generate_setup(self, user_id: str, **kwargs) -> MFASetup:
        """Generate MFA setup for a user."""
        pass

    @abstractmethod
    def verify(self, setup: MFASetup, code: str) -> bool:
        """Verify an MFA code."""
        pass


class TOTPProvider(MFAProvider):
    """
    TOTP (Time-based One-Time Password) provider.

    Compatible with Google Authenticator, Authy, etc.
    """

    def __init__(
        self,
        issuer: str = "PiMeet",
        digits: int = 6,
        interval: int = 30,
        algorithm: str = "sha1",
    ):
        """
        Initialize TOTP provider.

        Args:
            issuer: Application name for authenticator apps
            digits: Number of digits in code
            interval: Time interval in seconds
            algorithm: Hash algorithm
        """
        self._issuer = issuer
        self._digits = digits
        self._interval = interval
        self._algorithm = algorithm

    def generate_setup(self, user_id: str, **kwargs) -> MFASetup:
        """Generate TOTP setup."""
        # Generate random secret (160 bits = 32 base32 chars)
        secret_bytes = secrets.token_bytes(20)
        secret = base64.b32encode(secret_bytes).decode('ascii')

        return MFASetup(
            mfa_type=MFAType.TOTP,
            secret=secret,
        )

    def get_provisioning_uri(self, setup: MFASetup, account_name: str) -> str:
        """
        Get provisioning URI for QR code.

        Args:
            setup: MFA setup
            account_name: User account name/email

        Returns:
            otpauth:// URI
        """
        params = {
            "secret": setup.secret,
            "issuer": self._issuer,
            "algorithm": self._algorithm.upper(),
            "digits": str(self._digits),
            "period": str(self._interval),
        }

        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        return f"otpauth://totp/{self._issuer}:{account_name}?{param_str}"

    def verify(self, setup: MFASetup, code: str) -> bool:
        """Verify TOTP code."""
        if not setup.secret:
            return False

        # Allow 1 interval tolerance for clock skew
        for offset in [-1, 0, 1]:
            if self._generate_code(setup.secret, offset) == code:
                return True

        return False

    def _generate_code(self, secret: str, offset: int = 0) -> str:
        """Generate TOTP code for current time with offset."""
        # Decode secret
        try:
            key = base64.b32decode(secret.upper())
        except Exception:
            return ""

        # Calculate counter
        counter = (int(time.time()) // self._interval) + offset

        # HMAC-SHA1
        counter_bytes = struct.pack(">Q", counter)
        hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()

        # Dynamic truncation
        offset_byte = hmac_hash[-1] & 0x0F
        truncated = struct.unpack(">I", hmac_hash[offset_byte:offset_byte + 4])[0]
        truncated &= 0x7FFFFFFF

        # Generate code
        code = truncated % (10 ** self._digits)
        return str(code).zfill(self._digits)


class BackupCodeProvider(MFAProvider):
    """Backup code provider for account recovery."""

    def __init__(self, code_count: int = 10, code_length: int = 8):
        """
        Initialize backup code provider.

        Args:
            code_count: Number of backup codes to generate
            code_length: Length of each code
        """
        self._code_count = code_count
        self._code_length = code_length

    def generate_setup(self, user_id: str, **kwargs) -> MFASetup:
        """Generate backup codes."""
        codes = [
            secrets.token_hex(self._code_length // 2).upper()
            for _ in range(self._code_count)
        ]

        return MFASetup(
            mfa_type=MFAType.BACKUP_CODE,
            backup_codes=codes,
        )

    def verify(self, setup: MFASetup, code: str) -> bool:
        """Verify and consume a backup code."""
        if not setup.backup_codes:
            return False

        code = code.upper().replace("-", "").replace(" ", "")

        if code in setup.backup_codes:
            # Remove used code
            setup.backup_codes.remove(code)
            return True

        return False


@dataclass
class Session:
    """
    User session.

    Tracks authenticated sessions with security metadata.
    """
    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=8))
    last_activity: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    mfa_verified: bool = False
    roles: List[str] = field(default_factory=list)
    permissions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_active(self) -> bool:
        """Check if session is active (not expired and recent activity)."""
        if self.is_expired:
            return False
        # Session inactive after 1 hour of no activity
        inactive_threshold = datetime.utcnow() - timedelta(hours=1)
        return self.last_activity > inactive_threshold

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def extend(self, hours: int = 8) -> None:
        """Extend session expiration."""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "mfa_verified": self.mfa_verified,
            "roles": self.roles,
            "permissions": list(self.permissions),
        }


class SessionManager:
    """
    Session management service.

    Handles session creation, validation, and cleanup.
    """

    def __init__(
        self,
        session_timeout: int = 8,  # Hours
        max_sessions_per_user: int = 5,
        session_storage_path: Optional[Path] = None,
    ):
        """
        Initialize session manager.

        Args:
            session_timeout: Session timeout in hours
            max_sessions_per_user: Maximum concurrent sessions per user
            session_storage_path: Optional path for persistent session storage
        """
        self._timeout = timedelta(hours=session_timeout)
        self._max_sessions = max_sessions_per_user
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        self._storage_path = session_storage_path

        if session_storage_path:
            self._load_sessions()

    def create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        roles: Optional[List[str]] = None,
        permissions: Optional[Set[str]] = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: Client user agent
            roles: User roles
            permissions: User permissions

        Returns:
            New Session object
        """
        # Check max sessions
        if user_id in self._user_sessions:
            if len(self._user_sessions[user_id]) >= self._max_sessions:
                # Remove oldest session
                oldest = min(
                    (self._sessions[sid] for sid in self._user_sessions[user_id]),
                    key=lambda s: s.created_at,
                )
                self.invalidate(oldest.session_id)

        # Create session
        session_id = secrets.token_urlsafe(32)
        session = Session(
            session_id=session_id,
            user_id=user_id,
            expires_at=datetime.utcnow() + self._timeout,
            ip_address=ip_address,
            user_agent=user_agent,
            roles=roles or [],
            permissions=permissions or set(),
        )

        # Store session
        self._sessions[session_id] = session

        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(session_id)

        self._save_sessions()

        logger.info(f"Created session for user {user_id}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session or None if not found/expired
        """
        session = self._sessions.get(session_id)

        if session is None:
            return None

        if session.is_expired:
            self.invalidate(session_id)
            return None

        # Update activity
        session.touch()
        return session

    def validate_session(self, session_id: str) -> bool:
        """
        Validate a session is active and not expired.

        Args:
            session_id: Session ID

        Returns:
            True if session is valid
        """
        session = self.get_session(session_id)
        return session is not None and session.is_active

    def invalidate(self, session_id: str) -> bool:
        """
        Invalidate a session.

        Args:
            session_id: Session ID to invalidate

        Returns:
            True if session was invalidated
        """
        session = self._sessions.get(session_id)

        if session is None:
            return False

        # Remove from storage
        del self._sessions[session_id]

        if session.user_id in self._user_sessions:
            self._user_sessions[session.user_id].discard(session_id)
            if not self._user_sessions[session.user_id]:
                del self._user_sessions[session.user_id]

        self._save_sessions()

        logger.info(f"Invalidated session {session_id}")
        return True

    def invalidate_all_for_user(self, user_id: str) -> int:
        """
        Invalidate all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            Number of sessions invalidated
        """
        session_ids = self._user_sessions.get(user_id, set()).copy()

        for session_id in session_ids:
            self.invalidate(session_id)

        return len(session_ids)

    def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all sessions for a user."""
        session_ids = self._user_sessions.get(user_id, set())
        return [
            self._sessions[sid]
            for sid in session_ids
            if sid in self._sessions and not self._sessions[sid].is_expired
        ]

    def cleanup_expired(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        expired = [
            sid for sid, session in self._sessions.items()
            if session.is_expired
        ]

        for session_id in expired:
            self.invalidate(session_id)

        return len(expired)

    def _load_sessions(self) -> None:
        """Load sessions from storage."""
        if not self._storage_path or not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, 'r') as f:
                data = json.load(f)

            for session_data in data.get("sessions", []):
                session = Session(
                    session_id=session_data["session_id"],
                    user_id=session_data["user_id"],
                    created_at=datetime.fromisoformat(session_data["created_at"]),
                    expires_at=datetime.fromisoformat(session_data["expires_at"]),
                    last_activity=datetime.fromisoformat(session_data["last_activity"]),
                    ip_address=session_data.get("ip_address"),
                    user_agent=session_data.get("user_agent"),
                    mfa_verified=session_data.get("mfa_verified", False),
                    roles=session_data.get("roles", []),
                    permissions=set(session_data.get("permissions", [])),
                )

                if not session.is_expired:
                    self._sessions[session.session_id] = session

                    if session.user_id not in self._user_sessions:
                        self._user_sessions[session.user_id] = set()
                    self._user_sessions[session.user_id].add(session.session_id)

        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")

    def _save_sessions(self) -> None:
        """Save sessions to storage."""
        if not self._storage_path:
            return

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "sessions": [
                    session.to_dict()
                    for session in self._sessions.values()
                    if not session.is_expired
                ],
            }

            with open(self._storage_path, 'w') as f:
                json.dump(data, f)

            os.chmod(self._storage_path, 0o600)

        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")


class AuthenticationService:
    """
    Main authentication service.

    Coordinates password validation, MFA, and session management.
    """

    def __init__(
        self,
        password_policy: Optional[PasswordPolicy] = None,
        session_manager: Optional[SessionManager] = None,
        require_mfa: bool = False,
    ):
        """
        Initialize authentication service.

        Args:
            password_policy: Password policy configuration
            session_manager: Session manager instance
            require_mfa: Whether MFA is required
        """
        self._password_policy = password_policy or PasswordPolicy()
        self._session_manager = session_manager or SessionManager()
        self._require_mfa = require_mfa

        # MFA providers
        self._totp_provider = TOTPProvider()
        self._backup_provider = BackupCodeProvider()

        # User MFA setups (in production, this would be in database)
        self._mfa_setups: Dict[str, List[MFASetup]] = {}

    @property
    def password_policy(self) -> PasswordPolicy:
        """Get the password policy."""
        return self._password_policy

    @property
    def session_manager(self) -> SessionManager:
        """Get the session manager."""
        return self._session_manager

    def validate_password(
        self,
        password: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate a password against the policy.

        Args:
            password: Password to validate
            username: Username for similarity check
            email: Email for similarity check

        Returns:
            Tuple of (is_valid, violation messages)
        """
        return self._password_policy.validate(password, username, email)

    def get_password_strength(self, password: str) -> PasswordStrength:
        """Get password strength rating."""
        return self._password_policy.get_strength(password)

    def hash_password(self, password: str) -> str:
        """
        Hash a password for storage.

        Uses Argon2id for memory-hard hashing.

        Args:
            password: Password to hash

        Returns:
            Hashed password string
        """
        try:
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            return ph.hash(password)
        except ImportError:
            # Fallback to PBKDF2
            from pimeet.security.encryption import KeyDerivation
            derived = KeyDerivation.derive_pbkdf2(password)
            salt_b64 = base64.b64encode(derived.salt).decode()
            key_b64 = base64.b64encode(derived.key).decode()
            return f"pbkdf2:{salt_b64}:{key_b64}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            password: Password to verify
            password_hash: Stored password hash

        Returns:
            True if password matches
        """
        try:
            if password_hash.startswith("pbkdf2:"):
                # PBKDF2 fallback format
                _, salt_b64, key_b64 = password_hash.split(":")
                salt = base64.b64decode(salt_b64)
                stored_key = base64.b64decode(key_b64)

                from pimeet.security.encryption import KeyDerivation
                derived = KeyDerivation.derive_pbkdf2(password, salt)
                return hmac.compare_digest(derived.key, stored_key)
            else:
                # Argon2 format
                from argon2 import PasswordHasher
                from argon2.exceptions import VerifyMismatchError
                ph = PasswordHasher()
                try:
                    ph.verify(password_hash, password)
                    return True
                except VerifyMismatchError:
                    return False

        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def setup_mfa(
        self,
        user_id: str,
        mfa_type: MFAType = MFAType.TOTP,
    ) -> MFASetup:
        """
        Set up MFA for a user.

        Args:
            user_id: User ID
            mfa_type: Type of MFA to set up

        Returns:
            MFA setup information
        """
        if mfa_type == MFAType.TOTP:
            setup = self._totp_provider.generate_setup(user_id)
        elif mfa_type == MFAType.BACKUP_CODE:
            setup = self._backup_provider.generate_setup(user_id)
        else:
            raise ValueError(f"Unsupported MFA type: {mfa_type}")

        # Store setup
        if user_id not in self._mfa_setups:
            self._mfa_setups[user_id] = []
        self._mfa_setups[user_id].append(setup)

        return setup

    def verify_mfa(
        self,
        user_id: str,
        code: str,
        mfa_type: Optional[MFAType] = None,
    ) -> bool:
        """
        Verify an MFA code.

        Args:
            user_id: User ID
            code: MFA code
            mfa_type: Optional specific MFA type to verify

        Returns:
            True if code is valid
        """
        setups = self._mfa_setups.get(user_id, [])

        for setup in setups:
            if mfa_type and setup.mfa_type != mfa_type:
                continue

            if setup.mfa_type == MFAType.TOTP:
                if self._totp_provider.verify(setup, code):
                    setup.last_used = datetime.utcnow()
                    return True

            elif setup.mfa_type == MFAType.BACKUP_CODE:
                if self._backup_provider.verify(setup, code):
                    setup.last_used = datetime.utcnow()
                    return True

        return False

    def get_totp_uri(self, user_id: str, account_name: str) -> Optional[str]:
        """Get TOTP provisioning URI for QR code."""
        setups = self._mfa_setups.get(user_id, [])

        for setup in setups:
            if setup.mfa_type == MFAType.TOTP:
                return self._totp_provider.get_provisioning_uri(setup, account_name)

        return None

    def create_authenticated_session(
        self,
        user_id: str,
        mfa_verified: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        roles: Optional[List[str]] = None,
        permissions: Optional[Set[str]] = None,
    ) -> Session:
        """
        Create an authenticated session.

        Args:
            user_id: User ID
            mfa_verified: Whether MFA was verified
            ip_address: Client IP
            user_agent: Client user agent
            roles: User roles
            permissions: User permissions

        Returns:
            New session
        """
        session = self._session_manager.create_session(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            roles=roles,
            permissions=permissions,
        )
        session.mfa_verified = mfa_verified

        return session

    def is_mfa_required(self, user_id: str) -> bool:
        """Check if MFA is required for a user."""
        return self._require_mfa or user_id in self._mfa_setups

    def has_mfa_setup(self, user_id: str) -> bool:
        """Check if user has MFA set up."""
        return user_id in self._mfa_setups and len(self._mfa_setups[user_id]) > 0
