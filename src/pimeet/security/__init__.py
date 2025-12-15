"""
Security module for PiMeet Enterprise.

Provides comprehensive security features:
- Credential encryption (AES-256-GCM)
- TLS configuration and certificate management
- Authentication (MFA, SSO)
- Authorization (RBAC)
- Audit logging
- API security (JWT, rate limiting)
"""

from pimeet.security.credentials import (
    CredentialVault,
    CredentialType,
    CredentialStatus,
    SecureCredential,
    create_credential_vault,
)
from pimeet.security.encryption import (
    EncryptionService,
    KeyDerivation,
    KeyDerivationAlgorithm,
    DerivedKey,
    SecureKeyStorage,
    FileKeyStorage,
    LinuxKeyringStorage,
    TPMKeyStorage,
    create_key_storage,
)
from pimeet.security.auth import (
    AuthenticationService,
    PasswordPolicy,
    PasswordStrength,
    MFAProvider,
    MFAType,
    MFASetup,
    TOTPProvider,
    BackupCodeProvider,
    Session,
    SessionManager,
)
from pimeet.security.rbac import (
    RBACService,
    Role,
    Permission,
    ResourceType,
    ResourceScope,
    AccessDecision,
    DEFAULT_ROLES,
    create_rbac_service,
)
from pimeet.security.audit import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    AuditActor,
    AuditResource,
    SIEMExporter,
    create_audit_logger,
)
from pimeet.security.tls import (
    TLSConfig,
    CertificateManager,
    Certificate,
    create_tls_config,
)
from pimeet.security.sso import (
    SSOService,
    SSOProvider,
    SSOUser,
    SAMLConfig,
    SAMLAuthenticator,
    OIDCConfig,
    OIDCAuthenticator,
    LDAPConfig,
    LDAPAuthenticator,
)
from pimeet.security.api import (
    APISecurityService,
    JWTService,
    JWTConfig,
    TokenPayload,
    TokenType,
    RateLimiter,
    RateLimitConfig,
    InputValidator,
    CSRFProtection,
    create_api_security,
)
from pimeet.security.compliance import (
    TrustServiceCategory,
    ComplianceStatus,
    ControlFamily,
    ControlPoint,
    ComplianceEvidence,
    ComplianceCheckResult,
    ComplianceReport,
    ComplianceCheck,
    SOC2ComplianceService,
    SOC2_CONTROL_POINTS,
)

__all__ = [
    # Credentials
    "CredentialVault",
    "CredentialType",
    "CredentialStatus",
    "SecureCredential",
    "create_credential_vault",
    # Encryption
    "EncryptionService",
    "KeyDerivation",
    "KeyDerivationAlgorithm",
    "DerivedKey",
    "SecureKeyStorage",
    "FileKeyStorage",
    "LinuxKeyringStorage",
    "TPMKeyStorage",
    "create_key_storage",
    # Authentication
    "AuthenticationService",
    "PasswordPolicy",
    "PasswordStrength",
    "MFAProvider",
    "MFAType",
    "MFASetup",
    "TOTPProvider",
    "BackupCodeProvider",
    "Session",
    "SessionManager",
    # RBAC
    "RBACService",
    "Role",
    "Permission",
    "ResourceType",
    "ResourceScope",
    "AccessDecision",
    "DEFAULT_ROLES",
    "create_rbac_service",
    # Audit
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    "AuditActor",
    "AuditResource",
    "SIEMExporter",
    "create_audit_logger",
    # TLS
    "TLSConfig",
    "CertificateManager",
    "Certificate",
    "create_tls_config",
    # SSO
    "SSOService",
    "SSOProvider",
    "SSOUser",
    "SAMLConfig",
    "SAMLAuthenticator",
    "OIDCConfig",
    "OIDCAuthenticator",
    "LDAPConfig",
    "LDAPAuthenticator",
    # API Security
    "APISecurityService",
    "JWTService",
    "JWTConfig",
    "TokenPayload",
    "TokenType",
    "RateLimiter",
    "RateLimitConfig",
    "InputValidator",
    "CSRFProtection",
    "create_api_security",
    # SOC 2 Compliance
    "TrustServiceCategory",
    "ComplianceStatus",
    "ControlFamily",
    "ControlPoint",
    "ComplianceEvidence",
    "ComplianceCheckResult",
    "ComplianceReport",
    "ComplianceCheck",
    "SOC2ComplianceService",
    "SOC2_CONTROL_POINTS",
]
