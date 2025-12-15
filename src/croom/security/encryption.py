"""
Encryption services for Croom.

Provides AES-256-GCM encryption with secure key derivation.
"""

import base64
import hashlib
import hmac
import logging
import os
import secrets
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Encryption constants
SALT_SIZE = 32
NONCE_SIZE = 12
TAG_SIZE = 16
KEY_SIZE = 32  # 256 bits
ITERATION_COUNT = 600000  # OWASP recommended for PBKDF2-SHA256


class KeyDerivationAlgorithm(Enum):
    """Key derivation algorithms."""
    PBKDF2_SHA256 = "pbkdf2_sha256"
    ARGON2ID = "argon2id"
    SCRYPT = "scrypt"


@dataclass
class DerivedKey:
    """Container for derived key and metadata."""
    key: bytes
    salt: bytes
    algorithm: KeyDerivationAlgorithm
    iterations: int

    def to_dict(self) -> dict:
        return {
            "salt": base64.b64encode(self.salt).decode(),
            "algorithm": self.algorithm.value,
            "iterations": self.iterations,
        }

    @classmethod
    def from_dict(cls, data: dict, key: bytes) -> "DerivedKey":
        return cls(
            key=key,
            salt=base64.b64decode(data["salt"]),
            algorithm=KeyDerivationAlgorithm(data["algorithm"]),
            iterations=data.get("iterations", ITERATION_COUNT),
        )


class KeyDerivation:
    """
    Secure key derivation from passwords/secrets.

    Supports multiple KDF algorithms for flexibility.
    """

    @staticmethod
    def derive_pbkdf2(
        password: Union[str, bytes],
        salt: Optional[bytes] = None,
        iterations: int = ITERATION_COUNT,
    ) -> DerivedKey:
        """
        Derive a key using PBKDF2-SHA256.

        Args:
            password: Password or secret to derive from
            salt: Optional salt (generated if not provided)
            iterations: Number of iterations

        Returns:
            DerivedKey with key material and metadata
        """
        if isinstance(password, str):
            password = password.encode('utf-8')

        if salt is None:
            salt = secrets.token_bytes(SALT_SIZE)

        key = hashlib.pbkdf2_hmac(
            'sha256',
            password,
            salt,
            iterations,
            dklen=KEY_SIZE,
        )

        return DerivedKey(
            key=key,
            salt=salt,
            algorithm=KeyDerivationAlgorithm.PBKDF2_SHA256,
            iterations=iterations,
        )

    @staticmethod
    def derive_argon2(
        password: Union[str, bytes],
        salt: Optional[bytes] = None,
        time_cost: int = 3,
        memory_cost: int = 65536,
        parallelism: int = 4,
    ) -> DerivedKey:
        """
        Derive a key using Argon2id.

        Args:
            password: Password or secret to derive from
            salt: Optional salt (generated if not provided)
            time_cost: Number of iterations
            memory_cost: Memory in KB
            parallelism: Degree of parallelism

        Returns:
            DerivedKey with key material and metadata
        """
        try:
            from argon2.low_level import hash_secret_raw, Type
        except ImportError:
            logger.warning("argon2-cffi not available, falling back to PBKDF2")
            return KeyDerivation.derive_pbkdf2(password, salt)

        if isinstance(password, str):
            password = password.encode('utf-8')

        if salt is None:
            salt = secrets.token_bytes(SALT_SIZE)

        key = hash_secret_raw(
            secret=password,
            salt=salt,
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=KEY_SIZE,
            type=Type.ID,
        )

        return DerivedKey(
            key=key,
            salt=salt,
            algorithm=KeyDerivationAlgorithm.ARGON2ID,
            iterations=time_cost,
        )

    @staticmethod
    def derive_scrypt(
        password: Union[str, bytes],
        salt: Optional[bytes] = None,
        n: int = 2**17,  # CPU/memory cost
        r: int = 8,      # Block size
        p: int = 1,      # Parallelization
    ) -> DerivedKey:
        """
        Derive a key using scrypt.

        Args:
            password: Password or secret to derive from
            salt: Optional salt (generated if not provided)
            n: CPU/memory cost parameter
            r: Block size
            p: Parallelization parameter

        Returns:
            DerivedKey with key material and metadata
        """
        if isinstance(password, str):
            password = password.encode('utf-8')

        if salt is None:
            salt = secrets.token_bytes(SALT_SIZE)

        key = hashlib.scrypt(
            password,
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=KEY_SIZE,
        )

        return DerivedKey(
            key=key,
            salt=salt,
            algorithm=KeyDerivationAlgorithm.SCRYPT,
            iterations=n,
        )


class EncryptionService:
    """
    AES-256-GCM encryption service.

    Provides authenticated encryption with associated data (AEAD).
    """

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize encryption service.

        Args:
            key: 256-bit encryption key (generated if not provided)
        """
        if key is None:
            key = secrets.token_bytes(KEY_SIZE)

        if len(key) != KEY_SIZE:
            raise ValueError(f"Key must be {KEY_SIZE} bytes")

        self._key = key
        self._cipher_available = self._check_cipher_availability()

    def _check_cipher_availability(self) -> bool:
        """Check if cryptography library is available."""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            return True
        except ImportError:
            logger.warning("cryptography library not available")
            return False

    @property
    def key(self) -> bytes:
        """Get the encryption key."""
        return self._key

    def encrypt(
        self,
        plaintext: Union[str, bytes],
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """
        Encrypt data using AES-256-GCM.

        Args:
            plaintext: Data to encrypt
            associated_data: Additional authenticated data (not encrypted)

        Returns:
            Encrypted data (nonce || ciphertext || tag)
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')

        if not self._cipher_available:
            return self._encrypt_fallback(plaintext, associated_data)

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = secrets.token_bytes(NONCE_SIZE)
        aesgcm = AESGCM(self._key)

        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)

        # Format: nonce || ciphertext (includes tag)
        return nonce + ciphertext

    def decrypt(
        self,
        ciphertext: bytes,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """
        Decrypt data using AES-256-GCM.

        Args:
            ciphertext: Encrypted data (nonce || ciphertext || tag)
            associated_data: Additional authenticated data

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails (invalid key, corrupted data, etc.)
        """
        if len(ciphertext) < NONCE_SIZE + TAG_SIZE:
            raise ValueError("Ciphertext too short")

        if not self._cipher_available:
            return self._decrypt_fallback(ciphertext, associated_data)

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.exceptions import InvalidTag

        nonce = ciphertext[:NONCE_SIZE]
        actual_ciphertext = ciphertext[NONCE_SIZE:]

        aesgcm = AESGCM(self._key)

        try:
            return aesgcm.decrypt(nonce, actual_ciphertext, associated_data)
        except InvalidTag:
            raise ValueError("Decryption failed: invalid tag or corrupted data")

    def _encrypt_fallback(
        self,
        plaintext: bytes,
        associated_data: Optional[bytes],
    ) -> bytes:
        """Fallback encryption using Fernet (less secure but available in stdlib)."""
        from cryptography.fernet import Fernet

        # Derive Fernet key from our key
        fernet_key = base64.urlsafe_b64encode(self._key)
        f = Fernet(fernet_key)

        return f.encrypt(plaintext)

    def _decrypt_fallback(
        self,
        ciphertext: bytes,
        associated_data: Optional[bytes],
    ) -> bytes:
        """Fallback decryption using Fernet."""
        from cryptography.fernet import Fernet

        fernet_key = base64.urlsafe_b64encode(self._key)
        f = Fernet(fernet_key)

        return f.decrypt(ciphertext)

    def encrypt_to_base64(
        self,
        plaintext: Union[str, bytes],
        associated_data: Optional[bytes] = None,
    ) -> str:
        """Encrypt and return base64-encoded result."""
        ciphertext = self.encrypt(plaintext, associated_data)
        return base64.b64encode(ciphertext).decode('ascii')

    def decrypt_from_base64(
        self,
        ciphertext_b64: str,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt base64-encoded ciphertext."""
        ciphertext = base64.b64decode(ciphertext_b64)
        return self.decrypt(ciphertext, associated_data)

    @staticmethod
    def generate_key() -> bytes:
        """Generate a random 256-bit encryption key."""
        return secrets.token_bytes(KEY_SIZE)

    @staticmethod
    def derive_key(
        password: str,
        salt: Optional[bytes] = None,
        algorithm: KeyDerivationAlgorithm = KeyDerivationAlgorithm.ARGON2ID,
    ) -> DerivedKey:
        """
        Derive an encryption key from a password.

        Args:
            password: Password to derive from
            salt: Optional salt
            algorithm: KDF algorithm to use

        Returns:
            DerivedKey with key and metadata
        """
        if algorithm == KeyDerivationAlgorithm.ARGON2ID:
            return KeyDerivation.derive_argon2(password, salt)
        elif algorithm == KeyDerivationAlgorithm.SCRYPT:
            return KeyDerivation.derive_scrypt(password, salt)
        else:
            return KeyDerivation.derive_pbkdf2(password, salt)


class SecureKeyStorage(ABC):
    """Abstract base class for secure key storage backends."""

    @abstractmethod
    def store_key(self, key_id: str, key: bytes) -> bool:
        """Store a key securely."""
        pass

    @abstractmethod
    def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve a stored key."""
        pass

    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """Delete a stored key."""
        pass

    @abstractmethod
    def key_exists(self, key_id: str) -> bool:
        """Check if a key exists."""
        pass


class FileKeyStorage(SecureKeyStorage):
    """
    File-based key storage with encryption.

    Keys are stored in encrypted files with restricted permissions.
    """

    def __init__(self, storage_path: Path, master_key: bytes):
        """
        Initialize file-based key storage.

        Args:
            storage_path: Directory to store keys
            master_key: Master key for encrypting stored keys
        """
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._cipher = EncryptionService(master_key)

        # Set restrictive permissions on storage directory
        try:
            os.chmod(self._storage_path, 0o700)
        except OSError:
            logger.warning("Could not set permissions on key storage directory")

    def _key_path(self, key_id: str) -> Path:
        """Get path for a key file."""
        # Sanitize key_id to prevent directory traversal
        safe_id = hashlib.sha256(key_id.encode()).hexdigest()
        return self._storage_path / f"{safe_id}.key"

    def store_key(self, key_id: str, key: bytes) -> bool:
        """Store a key securely."""
        try:
            encrypted = self._cipher.encrypt(key)
            key_path = self._key_path(key_id)

            with open(key_path, 'wb') as f:
                f.write(encrypted)

            # Set restrictive permissions
            os.chmod(key_path, 0o600)

            logger.debug(f"Stored key: {key_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store key {key_id}: {e}")
            return False

    def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve a stored key."""
        try:
            key_path = self._key_path(key_id)

            if not key_path.exists():
                return None

            with open(key_path, 'rb') as f:
                encrypted = f.read()

            return self._cipher.decrypt(encrypted)

        except Exception as e:
            logger.error(f"Failed to retrieve key {key_id}: {e}")
            return None

    def delete_key(self, key_id: str) -> bool:
        """Delete a stored key."""
        try:
            key_path = self._key_path(key_id)

            if key_path.exists():
                # Overwrite with random data before deletion
                with open(key_path, 'wb') as f:
                    f.write(secrets.token_bytes(256))
                key_path.unlink()

            logger.debug(f"Deleted key: {key_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete key {key_id}: {e}")
            return False

    def key_exists(self, key_id: str) -> bool:
        """Check if a key exists."""
        return self._key_path(key_id).exists()


class LinuxKeyringStorage(SecureKeyStorage):
    """
    Linux keyring-based key storage using secretstorage.

    Uses the system's secure credential storage (e.g., GNOME Keyring).
    """

    def __init__(self, service_name: str = "croom"):
        """
        Initialize Linux keyring storage.

        Args:
            service_name: Service name for keyring entries
        """
        self._service_name = service_name
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if secretstorage is available."""
        try:
            import secretstorage
            return True
        except ImportError:
            logger.warning("secretstorage not available")
            return False

    def store_key(self, key_id: str, key: bytes) -> bool:
        """Store a key in the system keyring."""
        if not self._available:
            return False

        try:
            import secretstorage

            connection = secretstorage.dbus_init()
            collection = secretstorage.get_default_collection(connection)

            # Encode key as base64 for storage
            key_b64 = base64.b64encode(key).decode('ascii')

            attributes = {
                "service": self._service_name,
                "key_id": key_id,
            }

            collection.create_item(
                f"{self._service_name}/{key_id}",
                attributes,
                key_b64.encode('utf-8'),
                replace=True,
            )

            logger.debug(f"Stored key in keyring: {key_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store key in keyring: {e}")
            return False

    def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve a key from the system keyring."""
        if not self._available:
            return None

        try:
            import secretstorage

            connection = secretstorage.dbus_init()
            collection = secretstorage.get_default_collection(connection)

            attributes = {
                "service": self._service_name,
                "key_id": key_id,
            }

            items = list(collection.search_items(attributes))

            if not items:
                return None

            key_b64 = items[0].get_secret().decode('utf-8')
            return base64.b64decode(key_b64)

        except Exception as e:
            logger.error(f"Failed to retrieve key from keyring: {e}")
            return None

    def delete_key(self, key_id: str) -> bool:
        """Delete a key from the system keyring."""
        if not self._available:
            return False

        try:
            import secretstorage

            connection = secretstorage.dbus_init()
            collection = secretstorage.get_default_collection(connection)

            attributes = {
                "service": self._service_name,
                "key_id": key_id,
            }

            items = list(collection.search_items(attributes))

            for item in items:
                item.delete()

            logger.debug(f"Deleted key from keyring: {key_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete key from keyring: {e}")
            return False

    def key_exists(self, key_id: str) -> bool:
        """Check if a key exists in the keyring."""
        return self.retrieve_key(key_id) is not None


class TPMKeyStorage(SecureKeyStorage):
    """
    TPM 2.0-based key storage.

    Uses the system's TPM for hardware-backed key protection.
    """

    def __init__(self):
        """Initialize TPM key storage."""
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if TPM is available."""
        try:
            # Check for TPM device
            if not Path("/dev/tpm0").exists():
                logger.info("TPM device not found")
                return False

            # Check for tpm2-tools
            import subprocess
            result = subprocess.run(
                ["tpm2_getrandom", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0

        except Exception as e:
            logger.info(f"TPM not available: {e}")
            return False

    @property
    def is_available(self) -> bool:
        """Check if TPM storage is available."""
        return self._available

    def store_key(self, key_id: str, key: bytes) -> bool:
        """Store a key protected by TPM."""
        if not self._available:
            return False

        # TPM key storage implementation would use tpm2-tools
        # This is a placeholder - full implementation requires TPM setup
        logger.warning("TPM key storage not fully implemented")
        return False

    def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve a TPM-protected key."""
        if not self._available:
            return None

        logger.warning("TPM key retrieval not fully implemented")
        return None

    def delete_key(self, key_id: str) -> bool:
        """Delete a TPM-protected key."""
        if not self._available:
            return False

        logger.warning("TPM key deletion not fully implemented")
        return False

    def key_exists(self, key_id: str) -> bool:
        """Check if a TPM-protected key exists."""
        return False


def create_key_storage(
    storage_type: str = "auto",
    **kwargs,
) -> SecureKeyStorage:
    """
    Create appropriate key storage backend.

    Args:
        storage_type: Type of storage ("auto", "file", "keyring", "tpm")
        **kwargs: Additional arguments for the storage backend

    Returns:
        SecureKeyStorage instance
    """
    if storage_type == "tpm":
        storage = TPMKeyStorage()
        if storage.is_available:
            return storage
        logger.warning("TPM not available, falling back")

    if storage_type in ("keyring", "auto"):
        storage = LinuxKeyringStorage(kwargs.get("service_name", "croom"))
        if storage._available:
            return storage
        if storage_type == "keyring":
            logger.warning("Keyring not available, falling back to file storage")

    # Default to file storage
    storage_path = kwargs.get("storage_path", Path("/var/lib/croom/keys"))
    master_key = kwargs.get("master_key")

    if master_key is None:
        # Generate or load master key
        master_key_path = storage_path / ".master"
        if master_key_path.exists():
            with open(master_key_path, 'rb') as f:
                master_key = f.read()
        else:
            master_key = secrets.token_bytes(KEY_SIZE)
            storage_path.mkdir(parents=True, exist_ok=True)
            with open(master_key_path, 'wb') as f:
                f.write(master_key)
            os.chmod(master_key_path, 0o600)

    return FileKeyStorage(storage_path, master_key)
