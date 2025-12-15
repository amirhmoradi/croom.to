"""
Credential vault for PiMeet.

Provides secure storage and management of sensitive credentials.
"""

import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from pimeet.security.encryption import (
    EncryptionService,
    KeyDerivation,
    create_key_storage,
)

logger = logging.getLogger(__name__)


class CredentialType(Enum):
    """Types of credentials."""
    MEETING_PLATFORM = "meeting_platform"
    CALENDAR_OAUTH = "calendar_oauth"
    DASHBOARD_API = "dashboard_api"
    WIFI_PASSWORD = "wifi_password"
    SSH_KEY = "ssh_key"
    CERTIFICATE = "certificate"
    API_KEY = "api_key"
    GENERIC = "generic"


class CredentialStatus(Enum):
    """Credential status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING_ROTATION = "pending_rotation"


@dataclass
class SecureCredential:
    """
    A securely stored credential.

    Attributes:
        credential_id: Unique identifier
        credential_type: Type of credential
        name: Human-readable name
        encrypted_data: Encrypted credential data
        metadata: Non-sensitive metadata
        created_at: Creation timestamp
        expires_at: Expiration timestamp (optional)
        last_accessed: Last access timestamp
        last_rotated: Last rotation timestamp
        status: Current status
        access_count: Number of times accessed
    """
    credential_id: str
    credential_type: CredentialType
    name: str
    encrypted_data: bytes
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    last_rotated: Optional[datetime] = None
    status: CredentialStatus = CredentialStatus.ACTIVE
    access_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if credential is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def needs_rotation(self) -> bool:
        """Check if credential needs rotation."""
        if self.status == CredentialStatus.PENDING_ROTATION:
            return True
        # Default: rotate every 90 days
        if self.last_rotated:
            return datetime.utcnow() - self.last_rotated > timedelta(days=90)
        return datetime.utcnow() - self.created_at > timedelta(days=90)

    def to_dict(self) -> dict:
        """Serialize to dictionary (excluding encrypted data)."""
        return {
            "credential_id": self.credential_id,
            "credential_type": self.credential_type.value,
            "name": self.name,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "last_rotated": self.last_rotated.isoformat() if self.last_rotated else None,
            "status": self.status.value,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: dict, encrypted_data: bytes) -> "SecureCredential":
        """Deserialize from dictionary."""
        return cls(
            credential_id=data["credential_id"],
            credential_type=CredentialType(data["credential_type"]),
            name=data["name"],
            encrypted_data=encrypted_data,
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            last_rotated=datetime.fromisoformat(data["last_rotated"]) if data.get("last_rotated") else None,
            status=CredentialStatus(data.get("status", "active")),
            access_count=data.get("access_count", 0),
        )


class CredentialVault:
    """
    Secure credential vault.

    Provides encrypted storage, access control, and audit logging
    for sensitive credentials.
    """

    def __init__(
        self,
        vault_path: Path,
        master_password: Optional[str] = None,
        device_secret: Optional[bytes] = None,
    ):
        """
        Initialize credential vault.

        Args:
            vault_path: Path to vault storage
            master_password: Master password for encryption
            device_secret: Device-specific secret for key derivation
        """
        self._vault_path = Path(vault_path)
        self._vault_path.mkdir(parents=True, exist_ok=True)

        # Set restrictive permissions
        try:
            os.chmod(self._vault_path, 0o700)
        except OSError:
            pass

        # Derive encryption key
        self._encryption_key = self._derive_vault_key(
            master_password,
            device_secret,
        )
        self._cipher = EncryptionService(self._encryption_key)

        # Credential storage
        self._credentials: Dict[str, SecureCredential] = {}
        self._index_path = self._vault_path / "vault_index.json"
        self._data_path = self._vault_path / "vault_data"
        self._data_path.mkdir(exist_ok=True)

        # Access callbacks
        self._on_credential_access: Optional[Callable[[str, str], None]] = None
        self._on_credential_change: Optional[Callable[[str, str], None]] = None

        # Load existing credentials
        self._load_index()

    def _derive_vault_key(
        self,
        master_password: Optional[str],
        device_secret: Optional[bytes],
    ) -> bytes:
        """Derive the vault encryption key."""
        # Load or create salt
        salt_path = self._vault_path / ".salt"

        if salt_path.exists():
            with open(salt_path, 'rb') as f:
                salt = f.read()
        else:
            salt = secrets.token_bytes(32)
            with open(salt_path, 'wb') as f:
                f.write(salt)
            os.chmod(salt_path, 0o600)

        # Build key material
        if master_password:
            password = master_password.encode('utf-8')
        else:
            password = b"default_vault_key"

        if device_secret:
            password = password + device_secret

        # Add device-specific entropy
        device_id = self._get_device_id()
        if device_id:
            password = password + device_id.encode('utf-8')

        # Derive key
        derived = KeyDerivation.derive_argon2(password, salt)
        return derived.key

    def _get_device_id(self) -> Optional[str]:
        """Get a device-specific identifier."""
        # Try to read Pi serial number
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        return line.split(':')[1].strip()
        except Exception:
            pass

        # Try machine-id
        try:
            with open('/etc/machine-id', 'r') as f:
                return f.read().strip()
        except Exception:
            pass

        return None

    def _load_index(self) -> None:
        """Load credential index from disk."""
        if not self._index_path.exists():
            return

        try:
            with open(self._index_path, 'rb') as f:
                encrypted_index = f.read()

            index_json = self._cipher.decrypt(encrypted_index).decode('utf-8')
            index_data = json.loads(index_json)

            for cred_id, cred_meta in index_data.items():
                # Load encrypted data
                data_file = self._data_path / f"{cred_id}.enc"
                if data_file.exists():
                    with open(data_file, 'rb') as f:
                        encrypted_data = f.read()

                    self._credentials[cred_id] = SecureCredential.from_dict(
                        cred_meta,
                        encrypted_data,
                    )

            logger.info(f"Loaded {len(self._credentials)} credentials from vault")

        except Exception as e:
            logger.error(f"Failed to load vault index: {e}")

    def _save_index(self) -> None:
        """Save credential index to disk."""
        try:
            index_data = {
                cred_id: cred.to_dict()
                for cred_id, cred in self._credentials.items()
            }

            index_json = json.dumps(index_data, indent=2)
            encrypted_index = self._cipher.encrypt(index_json.encode('utf-8'))

            with open(self._index_path, 'wb') as f:
                f.write(encrypted_index)

            os.chmod(self._index_path, 0o600)

        except Exception as e:
            logger.error(f"Failed to save vault index: {e}")

    def store(
        self,
        credential_type: CredentialType,
        name: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        expires_in: Optional[timedelta] = None,
        credential_id: Optional[str] = None,
    ) -> SecureCredential:
        """
        Store a credential securely.

        Args:
            credential_type: Type of credential
            name: Human-readable name
            data: Credential data to encrypt
            metadata: Non-sensitive metadata
            expires_in: Time until expiration
            credential_id: Optional specific ID

        Returns:
            Stored SecureCredential
        """
        if credential_id is None:
            credential_id = secrets.token_hex(16)

        # Encrypt the credential data
        data_json = json.dumps(data)
        encrypted_data = self._cipher.encrypt(data_json.encode('utf-8'))

        # Create credential object
        credential = SecureCredential(
            credential_id=credential_id,
            credential_type=credential_type,
            name=name,
            encrypted_data=encrypted_data,
            metadata=metadata or {},
            expires_at=datetime.utcnow() + expires_in if expires_in else None,
        )

        # Save encrypted data to file
        data_file = self._data_path / f"{credential_id}.enc"
        with open(data_file, 'wb') as f:
            f.write(encrypted_data)
        os.chmod(data_file, 0o600)

        # Store in memory and update index
        self._credentials[credential_id] = credential
        self._save_index()

        logger.info(f"Stored credential: {name} ({credential_type.value})")

        if self._on_credential_change:
            self._on_credential_change(credential_id, "created")

        return credential

    def retrieve(
        self,
        credential_id: str,
        accessor: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve and decrypt a credential.

        Args:
            credential_id: ID of credential to retrieve
            accessor: Identity of accessor (for audit)

        Returns:
            Decrypted credential data or None if not found
        """
        credential = self._credentials.get(credential_id)

        if credential is None:
            return None

        if credential.status == CredentialStatus.REVOKED:
            logger.warning(f"Attempted access to revoked credential: {credential_id}")
            return None

        if credential.is_expired:
            logger.warning(f"Credential expired: {credential_id}")
            credential.status = CredentialStatus.EXPIRED
            self._save_index()
            return None

        try:
            # Decrypt the data
            decrypted = self._cipher.decrypt(credential.encrypted_data)
            data = json.loads(decrypted.decode('utf-8'))

            # Update access tracking
            credential.last_accessed = datetime.utcnow()
            credential.access_count += 1
            self._save_index()

            # Audit callback
            if self._on_credential_access:
                self._on_credential_access(credential_id, accessor or "unknown")

            return data

        except Exception as e:
            logger.error(f"Failed to decrypt credential {credential_id}: {e}")
            return None

    def update(
        self,
        credential_id: str,
        data: Dict[str, Any],
        rotate: bool = False,
    ) -> bool:
        """
        Update a credential's data.

        Args:
            credential_id: ID of credential to update
            data: New credential data
            rotate: Whether this is a rotation

        Returns:
            True if updated successfully
        """
        credential = self._credentials.get(credential_id)

        if credential is None:
            return False

        try:
            # Encrypt new data
            data_json = json.dumps(data)
            encrypted_data = self._cipher.encrypt(data_json.encode('utf-8'))

            # Update credential
            credential.encrypted_data = encrypted_data

            if rotate:
                credential.last_rotated = datetime.utcnow()
                credential.status = CredentialStatus.ACTIVE

            # Save encrypted data
            data_file = self._data_path / f"{credential_id}.enc"
            with open(data_file, 'wb') as f:
                f.write(encrypted_data)

            self._save_index()

            logger.info(f"Updated credential: {credential.name}")

            if self._on_credential_change:
                self._on_credential_change(credential_id, "rotated" if rotate else "updated")

            return True

        except Exception as e:
            logger.error(f"Failed to update credential {credential_id}: {e}")
            return False

    def delete(self, credential_id: str) -> bool:
        """
        Delete a credential.

        Args:
            credential_id: ID of credential to delete

        Returns:
            True if deleted successfully
        """
        credential = self._credentials.get(credential_id)

        if credential is None:
            return False

        try:
            # Securely delete data file
            data_file = self._data_path / f"{credential_id}.enc"
            if data_file.exists():
                # Overwrite with random data
                with open(data_file, 'wb') as f:
                    f.write(secrets.token_bytes(len(credential.encrypted_data)))
                data_file.unlink()

            # Remove from memory and index
            del self._credentials[credential_id]
            self._save_index()

            logger.info(f"Deleted credential: {credential.name}")

            if self._on_credential_change:
                self._on_credential_change(credential_id, "deleted")

            return True

        except Exception as e:
            logger.error(f"Failed to delete credential {credential_id}: {e}")
            return False

    def revoke(self, credential_id: str) -> bool:
        """
        Revoke a credential (mark as unusable without deleting).

        Args:
            credential_id: ID of credential to revoke

        Returns:
            True if revoked successfully
        """
        credential = self._credentials.get(credential_id)

        if credential is None:
            return False

        credential.status = CredentialStatus.REVOKED
        self._save_index()

        logger.info(f"Revoked credential: {credential.name}")

        if self._on_credential_change:
            self._on_credential_change(credential_id, "revoked")

        return True

    def list_credentials(
        self,
        credential_type: Optional[CredentialType] = None,
        include_expired: bool = False,
    ) -> List[SecureCredential]:
        """
        List credentials (without decrypting).

        Args:
            credential_type: Filter by type
            include_expired: Include expired credentials

        Returns:
            List of credentials (data not decrypted)
        """
        result = []

        for credential in self._credentials.values():
            if credential_type and credential.credential_type != credential_type:
                continue
            if not include_expired and credential.is_expired:
                continue
            result.append(credential)

        return result

    def get_credentials_needing_rotation(self) -> List[SecureCredential]:
        """Get credentials that need rotation."""
        return [
            cred for cred in self._credentials.values()
            if cred.needs_rotation and cred.status == CredentialStatus.ACTIVE
        ]

    def schedule_rotation(self, credential_id: str) -> bool:
        """Schedule a credential for rotation."""
        credential = self._credentials.get(credential_id)

        if credential is None:
            return False

        credential.status = CredentialStatus.PENDING_ROTATION
        self._save_index()

        return True

    def on_access(self, callback: Callable[[str, str], None]) -> None:
        """Register callback for credential access events."""
        self._on_credential_access = callback

    def on_change(self, callback: Callable[[str, str], None]) -> None:
        """Register callback for credential change events."""
        self._on_credential_change = callback

    def export_metadata(self) -> Dict[str, Any]:
        """Export vault metadata (for backup/audit, no secrets)."""
        return {
            "credential_count": len(self._credentials),
            "credentials": [
                cred.to_dict()
                for cred in self._credentials.values()
            ],
            "exported_at": datetime.utcnow().isoformat(),
        }

    def change_master_password(
        self,
        old_password: str,
        new_password: str,
    ) -> bool:
        """
        Change the vault master password.

        Re-encrypts all credentials with new key.

        Args:
            old_password: Current master password
            new_password: New master password

        Returns:
            True if password changed successfully
        """
        # Verify old password
        old_key = self._derive_vault_key(old_password, None)
        if old_key != self._encryption_key:
            logger.error("Invalid old password")
            return False

        try:
            # Decrypt all credentials
            decrypted_data = {}
            for cred_id, cred in self._credentials.items():
                try:
                    decrypted = self._cipher.decrypt(cred.encrypted_data)
                    decrypted_data[cred_id] = decrypted
                except Exception:
                    logger.error(f"Failed to decrypt credential {cred_id}")
                    return False

            # Generate new salt and derive new key
            salt_path = self._vault_path / ".salt"
            new_salt = secrets.token_bytes(32)

            # Derive new key
            derived = KeyDerivation.derive_argon2(
                new_password.encode('utf-8'),
                new_salt,
            )

            # Create new cipher
            new_cipher = EncryptionService(derived.key)

            # Re-encrypt all credentials
            for cred_id, plaintext in decrypted_data.items():
                encrypted = new_cipher.encrypt(plaintext)
                self._credentials[cred_id].encrypted_data = encrypted

                # Save to file
                data_file = self._data_path / f"{cred_id}.enc"
                with open(data_file, 'wb') as f:
                    f.write(encrypted)

            # Update salt
            with open(salt_path, 'wb') as f:
                f.write(new_salt)

            # Update cipher and key
            self._encryption_key = derived.key
            self._cipher = new_cipher

            # Re-save index with new encryption
            self._save_index()

            logger.info("Vault master password changed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to change master password: {e}")
            return False


def create_credential_vault(
    config: Dict[str, Any],
) -> CredentialVault:
    """
    Create a credential vault from configuration.

    Args:
        config: Vault configuration

    Returns:
        Configured CredentialVault instance
    """
    vault_path = Path(config.get("vault_path", "/var/lib/pimeet/credentials"))
    master_password = config.get("master_password")
    device_secret = config.get("device_secret")

    if device_secret and isinstance(device_secret, str):
        device_secret = device_secret.encode('utf-8')

    return CredentialVault(
        vault_path=vault_path,
        master_password=master_password,
        device_secret=device_secret,
    )
