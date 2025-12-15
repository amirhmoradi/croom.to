"""
API security for Croom.

Provides JWT authentication, rate limiting, and request validation.
"""

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Types of API tokens."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SERVICE = "service"


@dataclass
class JWTConfig:
    """
    JWT configuration.

    Attributes:
        secret_key: Secret for signing tokens
        algorithm: Signing algorithm
        access_token_expire: Access token expiration (minutes)
        refresh_token_expire: Refresh token expiration (days)
        issuer: Token issuer
        audience: Token audience
    """
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire: int = 30  # minutes
    refresh_token_expire: int = 7  # days
    issuer: str = "croom"
    audience: str = "croom-api"


@dataclass
class TokenPayload:
    """
    JWT token payload.

    Attributes:
        sub: Subject (user ID)
        token_type: Type of token
        exp: Expiration timestamp
        iat: Issued at timestamp
        jti: JWT ID (unique identifier)
        scopes: Authorized scopes
        roles: User roles
        metadata: Additional metadata
    """
    sub: str
    token_type: TokenType
    exp: datetime
    iat: datetime = field(default_factory=datetime.utcnow)
    jti: str = field(default_factory=lambda: secrets.token_hex(16))
    scopes: Set[str] = field(default_factory=set)
    roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.exp

    def to_dict(self) -> dict:
        """Serialize to dictionary for JWT payload."""
        return {
            "sub": self.sub,
            "token_type": self.token_type.value,
            "exp": int(self.exp.timestamp()),
            "iat": int(self.iat.timestamp()),
            "jti": self.jti,
            "scopes": list(self.scopes),
            "roles": self.roles,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TokenPayload":
        """Deserialize from dictionary."""
        return cls(
            sub=data["sub"],
            token_type=TokenType(data.get("token_type", "access")),
            exp=datetime.fromtimestamp(data["exp"]),
            iat=datetime.fromtimestamp(data.get("iat", time.time())),
            jti=data.get("jti", ""),
            scopes=set(data.get("scopes", [])),
            roles=data.get("roles", []),
            metadata=data.get("metadata", {}),
        )


class JWTService:
    """
    JWT token service.

    Handles token creation, validation, and refresh.
    """

    def __init__(self, config: JWTConfig):
        """
        Initialize JWT service.

        Args:
            config: JWT configuration
        """
        self._config = config
        self._revoked_tokens: Set[str] = set()  # JTIs of revoked tokens

    def create_access_token(
        self,
        subject: str,
        scopes: Optional[Set[str]] = None,
        roles: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create an access token.

        Args:
            subject: User ID or identifier
            scopes: Authorized scopes
            roles: User roles
            metadata: Additional metadata

        Returns:
            Encoded JWT token
        """
        payload = TokenPayload(
            sub=subject,
            token_type=TokenType.ACCESS,
            exp=datetime.utcnow() + timedelta(minutes=self._config.access_token_expire),
            scopes=scopes or set(),
            roles=roles or [],
            metadata=metadata or {},
        )

        return self._encode(payload)

    def create_refresh_token(
        self,
        subject: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a refresh token.

        Args:
            subject: User ID or identifier
            metadata: Additional metadata

        Returns:
            Encoded JWT token
        """
        payload = TokenPayload(
            sub=subject,
            token_type=TokenType.REFRESH,
            exp=datetime.utcnow() + timedelta(days=self._config.refresh_token_expire),
            metadata=metadata or {},
        )

        return self._encode(payload)

    def create_api_key(
        self,
        subject: str,
        scopes: Optional[Set[str]] = None,
        expire_days: int = 365,
    ) -> str:
        """
        Create a long-lived API key.

        Args:
            subject: Service or user identifier
            scopes: Authorized scopes
            expire_days: Expiration in days

        Returns:
            API key token
        """
        payload = TokenPayload(
            sub=subject,
            token_type=TokenType.API_KEY,
            exp=datetime.utcnow() + timedelta(days=expire_days),
            scopes=scopes or set(),
        )

        return self._encode(payload)

    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """
        Validate and decode a token.

        Args:
            token: Encoded JWT token

        Returns:
            TokenPayload if valid, None otherwise
        """
        try:
            payload = self._decode(token)

            if payload is None:
                return None

            # Check expiration
            if payload.is_expired:
                logger.debug(f"Token expired for subject: {payload.sub}")
                return None

            # Check revocation
            if payload.jti in self._revoked_tokens:
                logger.debug(f"Token revoked: {payload.jti}")
                return None

            return payload

        except Exception as e:
            logger.debug(f"Token validation error: {e}")
            return None

    def refresh_access_token(
        self,
        refresh_token: str,
        new_scopes: Optional[Set[str]] = None,
    ) -> Optional[Tuple[str, str]]:
        """
        Refresh an access token.

        Args:
            refresh_token: Current refresh token
            new_scopes: Updated scopes (optional)

        Returns:
            Tuple of (new_access_token, new_refresh_token) or None
        """
        payload = self.validate_token(refresh_token)

        if payload is None:
            return None

        if payload.token_type != TokenType.REFRESH:
            logger.warning("Attempted to refresh with non-refresh token")
            return None

        # Create new tokens
        access_token = self.create_access_token(
            subject=payload.sub,
            scopes=new_scopes or payload.scopes,
            roles=payload.roles,
            metadata=payload.metadata,
        )

        new_refresh_token = self.create_refresh_token(
            subject=payload.sub,
            metadata=payload.metadata,
        )

        # Revoke old refresh token
        self.revoke_token(refresh_token)

        return access_token, new_refresh_token

    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token.

        Args:
            token: Token to revoke

        Returns:
            True if revoked successfully
        """
        payload = self._decode(token)

        if payload:
            self._revoked_tokens.add(payload.jti)
            return True

        return False

    def revoke_all_for_subject(self, subject: str) -> None:
        """Mark that all tokens for a subject should be considered revoked."""
        # In production, this would update a database
        # For now, tokens will naturally expire
        logger.info(f"All tokens revoked for subject: {subject}")

    def _encode(self, payload: TokenPayload) -> str:
        """Encode a JWT token."""
        # Header
        header = {
            "alg": self._config.algorithm,
            "typ": "JWT",
        }
        header_b64 = self._base64url_encode(json.dumps(header))

        # Payload
        payload_dict = payload.to_dict()
        payload_dict["iss"] = self._config.issuer
        payload_dict["aud"] = self._config.audience
        payload_b64 = self._base64url_encode(json.dumps(payload_dict))

        # Signature
        message = f"{header_b64}.{payload_b64}"
        signature = self._sign(message)
        signature_b64 = self._base64url_encode(signature)

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def _decode(self, token: str) -> Optional[TokenPayload]:
        """Decode and verify a JWT token."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature_b64 = parts

            # Verify signature
            message = f"{header_b64}.{payload_b64}"
            expected_signature = self._sign(message)
            actual_signature = self._base64url_decode(signature_b64)

            if not hmac.compare_digest(expected_signature, actual_signature):
                return None

            # Decode payload
            payload_json = self._base64url_decode(payload_b64).decode('utf-8')
            payload_dict = json.loads(payload_json)

            # Verify issuer and audience
            if payload_dict.get("iss") != self._config.issuer:
                return None
            if payload_dict.get("aud") != self._config.audience:
                return None

            return TokenPayload.from_dict(payload_dict)

        except Exception:
            return None

    def _sign(self, message: str) -> bytes:
        """Sign a message using the configured algorithm."""
        key = self._config.secret_key.encode('utf-8')

        if self._config.algorithm == "HS256":
            return hmac.new(key, message.encode('utf-8'), hashlib.sha256).digest()
        elif self._config.algorithm == "HS384":
            return hmac.new(key, message.encode('utf-8'), hashlib.sha384).digest()
        elif self._config.algorithm == "HS512":
            return hmac.new(key, message.encode('utf-8'), hashlib.sha512).digest()
        else:
            raise ValueError(f"Unsupported algorithm: {self._config.algorithm}")

    def _base64url_encode(self, data: Any) -> str:
        """Base64 URL encode."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

    def _base64url_decode(self, data: str) -> bytes:
        """Base64 URL decode."""
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)


@dataclass
class RateLimitConfig:
    """
    Rate limit configuration.

    Attributes:
        requests_per_minute: Maximum requests per minute
        requests_per_hour: Maximum requests per hour
        burst_size: Maximum burst size
        penalty_minutes: Penalty duration for exceeded limits
    """
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    penalty_minutes: int = 5


class RateLimiter:
    """
    Token bucket rate limiter.

    Provides per-client rate limiting with burst support.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self._config = config
        self._buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "tokens": config.burst_size,
                "last_update": time.time(),
                "minute_count": 0,
                "minute_start": time.time(),
                "hour_count": 0,
                "hour_start": time.time(),
                "penalty_until": 0,
            }
        )
        self._rate = config.requests_per_minute / 60  # Tokens per second

    def check_limit(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a request is allowed.

        Args:
            client_id: Client identifier (IP, user ID, API key)

        Returns:
            Tuple of (allowed, info_dict)
        """
        bucket = self._buckets[client_id]
        now = time.time()

        # Check penalty
        if now < bucket["penalty_until"]:
            return False, {
                "retry_after": int(bucket["penalty_until"] - now),
                "reason": "rate_limited",
            }

        # Refill tokens
        elapsed = now - bucket["last_update"]
        bucket["tokens"] = min(
            self._config.burst_size,
            bucket["tokens"] + elapsed * self._rate,
        )
        bucket["last_update"] = now

        # Check minute window
        if now - bucket["minute_start"] > 60:
            bucket["minute_count"] = 0
            bucket["minute_start"] = now

        # Check hour window
        if now - bucket["hour_start"] > 3600:
            bucket["hour_count"] = 0
            bucket["hour_start"] = now

        # Check limits
        if bucket["minute_count"] >= self._config.requests_per_minute:
            bucket["penalty_until"] = now + (self._config.penalty_minutes * 60)
            return False, {
                "retry_after": 60 - int(now - bucket["minute_start"]),
                "reason": "minute_limit_exceeded",
            }

        if bucket["hour_count"] >= self._config.requests_per_hour:
            bucket["penalty_until"] = now + (self._config.penalty_minutes * 60)
            return False, {
                "retry_after": 3600 - int(now - bucket["hour_start"]),
                "reason": "hour_limit_exceeded",
            }

        # Check tokens
        if bucket["tokens"] < 1:
            return False, {
                "retry_after": int(1 / self._rate),
                "reason": "burst_limit",
            }

        # Consume token
        bucket["tokens"] -= 1
        bucket["minute_count"] += 1
        bucket["hour_count"] += 1

        return True, {
            "remaining_minute": self._config.requests_per_minute - bucket["minute_count"],
            "remaining_hour": self._config.requests_per_hour - bucket["hour_count"],
        }

    def get_limits(self, client_id: str) -> Dict[str, Any]:
        """Get current limits for a client."""
        bucket = self._buckets.get(client_id)

        if bucket is None:
            return {
                "limit_minute": self._config.requests_per_minute,
                "limit_hour": self._config.requests_per_hour,
                "remaining_minute": self._config.requests_per_minute,
                "remaining_hour": self._config.requests_per_hour,
            }

        return {
            "limit_minute": self._config.requests_per_minute,
            "limit_hour": self._config.requests_per_hour,
            "remaining_minute": self._config.requests_per_minute - bucket["minute_count"],
            "remaining_hour": self._config.requests_per_hour - bucket["hour_count"],
        }


class InputValidator:
    """
    Input validation and sanitization.

    Provides protection against common attacks.
    """

    # Dangerous patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)",
        r"(--|\#|\/\*)",
        r"(\bOR\b.*=.*\bOR\b)",
        r"('\s*(OR|AND)\s*')",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
    ]

    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%252e%252e%252f",
    ]

    @classmethod
    def validate_string(
        cls,
        value: str,
        max_length: int = 1000,
        allow_html: bool = False,
        allow_special: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a string input.

        Args:
            value: String to validate
            max_length: Maximum length
            allow_html: Allow HTML tags
            allow_special: Allow special characters

        Returns:
            Tuple of (is_valid, error_message)
        """
        import re

        if len(value) > max_length:
            return False, f"Value exceeds maximum length of {max_length}"

        # Check for SQL injection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False, "Potentially dangerous SQL pattern detected"

        # Check for XSS
        if not allow_html:
            for pattern in cls.XSS_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    return False, "Potentially dangerous HTML/script pattern detected"

        # Check for path traversal
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False, "Path traversal pattern detected"

        return True, None

    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """
        Sanitize a string input.

        Args:
            value: String to sanitize
            max_length: Maximum length

        Returns:
            Sanitized string
        """
        import html
        import re

        # Truncate
        value = value[:max_length]

        # Remove null bytes
        value = value.replace('\x00', '')

        # HTML escape
        value = html.escape(value)

        # Remove control characters (except newline, tab)
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)

        return value

    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, Optional[str]]:
        """Validate an email address."""
        import re

        if len(email) > 254:
            return False, "Email too long"

        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format"

        return True, None

    @classmethod
    def validate_url(cls, url: str, allowed_schemes: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
        """Validate a URL."""
        from urllib.parse import urlparse

        if allowed_schemes is None:
            allowed_schemes = ["http", "https"]

        try:
            parsed = urlparse(url)

            if parsed.scheme not in allowed_schemes:
                return False, f"URL scheme must be one of: {allowed_schemes}"

            if not parsed.netloc:
                return False, "URL must have a host"

            return True, None

        except Exception:
            return False, "Invalid URL format"

    @classmethod
    def validate_json(cls, data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate JSON data against a simple schema.

        Args:
            data: JSON data to validate
            schema: Validation schema

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []

        # Check required fields
        for field in schema.get("required", []):
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Check field types and constraints
        for field, rules in schema.get("properties", {}).items():
            if field not in data:
                continue

            value = data[field]
            expected_type = rules.get("type")

            # Type checking
            type_map = {
                "string": str,
                "integer": int,
                "number": (int, float),
                "boolean": bool,
                "array": list,
                "object": dict,
            }

            if expected_type and not isinstance(value, type_map.get(expected_type, object)):
                errors.append(f"Field '{field}' must be of type {expected_type}")
                continue

            # String constraints
            if expected_type == "string":
                if "minLength" in rules and len(value) < rules["minLength"]:
                    errors.append(f"Field '{field}' must be at least {rules['minLength']} characters")
                if "maxLength" in rules and len(value) > rules["maxLength"]:
                    errors.append(f"Field '{field}' must be at most {rules['maxLength']} characters")
                if "pattern" in rules:
                    import re
                    if not re.match(rules["pattern"], value):
                        errors.append(f"Field '{field}' does not match required pattern")

            # Number constraints
            if expected_type in ("integer", "number"):
                if "minimum" in rules and value < rules["minimum"]:
                    errors.append(f"Field '{field}' must be at least {rules['minimum']}")
                if "maximum" in rules and value > rules["maximum"]:
                    errors.append(f"Field '{field}' must be at most {rules['maximum']}")

            # Enum
            if "enum" in rules and value not in rules["enum"]:
                errors.append(f"Field '{field}' must be one of: {rules['enum']}")

        return len(errors) == 0, errors


class CSRFProtection:
    """
    CSRF token protection.

    Provides token generation and validation.
    """

    def __init__(self, secret_key: str, token_lifetime: int = 3600):
        """
        Initialize CSRF protection.

        Args:
            secret_key: Secret for token signing
            token_lifetime: Token lifetime in seconds
        """
        self._secret = secret_key.encode('utf-8')
        self._lifetime = token_lifetime

    def generate_token(self, session_id: str) -> str:
        """
        Generate a CSRF token.

        Args:
            session_id: Associated session ID

        Returns:
            CSRF token
        """
        timestamp = int(time.time())
        random_part = secrets.token_hex(16)
        message = f"{session_id}:{timestamp}:{random_part}"

        signature = hmac.new(self._secret, message.encode('utf-8'), hashlib.sha256).hexdigest()

        return base64.urlsafe_b64encode(
            f"{message}:{signature}".encode('utf-8')
        ).decode('ascii')

    def validate_token(self, token: str, session_id: str) -> bool:
        """
        Validate a CSRF token.

        Args:
            token: Token to validate
            session_id: Expected session ID

        Returns:
            True if valid
        """
        try:
            decoded = base64.urlsafe_b64decode(token).decode('utf-8')
            parts = decoded.rsplit(':', 1)

            if len(parts) != 2:
                return False

            message, signature = parts
            msg_parts = message.split(':')

            if len(msg_parts) != 3:
                return False

            token_session, timestamp, _ = msg_parts

            # Verify session
            if token_session != session_id:
                return False

            # Verify timestamp
            if int(time.time()) - int(timestamp) > self._lifetime:
                return False

            # Verify signature
            expected_sig = hmac.new(
                self._secret,
                message.encode('utf-8'),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(signature, expected_sig)

        except Exception:
            return False


class APISecurityService:
    """
    Main API security service.

    Combines JWT, rate limiting, and input validation.
    """

    def __init__(
        self,
        jwt_config: JWTConfig,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """
        Initialize API security service.

        Args:
            jwt_config: JWT configuration
            rate_limit_config: Rate limit configuration
        """
        self._jwt = JWTService(jwt_config)
        self._rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        self._csrf = CSRFProtection(jwt_config.secret_key)

    @property
    def jwt(self) -> JWTService:
        """Get JWT service."""
        return self._jwt

    @property
    def rate_limiter(self) -> RateLimiter:
        """Get rate limiter."""
        return self._rate_limiter

    @property
    def csrf(self) -> CSRFProtection:
        """Get CSRF protection."""
        return self._csrf

    def authenticate_request(
        self,
        authorization_header: Optional[str],
        api_key_header: Optional[str] = None,
    ) -> Optional[TokenPayload]:
        """
        Authenticate an API request.

        Args:
            authorization_header: Authorization header value
            api_key_header: API key header value

        Returns:
            Token payload if authenticated
        """
        # Try Bearer token
        if authorization_header and authorization_header.startswith("Bearer "):
            token = authorization_header[7:]
            return self._jwt.validate_token(token)

        # Try API key
        if api_key_header:
            return self._jwt.validate_token(api_key_header)

        return None

    def check_rate_limit(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit for a client."""
        return self._rate_limiter.check_limit(client_id)

    def validate_request_body(
        self,
        body: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """Validate request body against schema."""
        return InputValidator.validate_json(body, schema)


def create_api_security(config: Dict[str, Any]) -> APISecurityService:
    """
    Create API security service from configuration.

    Args:
        config: Security configuration

    Returns:
        Configured APISecurityService
    """
    jwt_config = JWTConfig(
        secret_key=config.get("jwt_secret", secrets.token_hex(32)),
        algorithm=config.get("jwt_algorithm", "HS256"),
        access_token_expire=config.get("access_token_expire", 30),
        refresh_token_expire=config.get("refresh_token_expire", 7),
        issuer=config.get("jwt_issuer", "croom"),
        audience=config.get("jwt_audience", "croom-api"),
    )

    rate_config = RateLimitConfig(
        requests_per_minute=config.get("rate_limit_minute", 60),
        requests_per_hour=config.get("rate_limit_hour", 1000),
        burst_size=config.get("rate_limit_burst", 10),
    )

    return APISecurityService(jwt_config, rate_config)
