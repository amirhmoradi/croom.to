"""
TLS configuration and certificate management for PiMeet.

Provides secure transport layer configuration and certificate handling.
"""

import asyncio
import logging
import os
import ssl
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Secure TLS cipher suites (TLS 1.3 and strong TLS 1.2)
TLS13_CIPHERS = [
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "TLS_AES_128_GCM_SHA256",
]

TLS12_CIPHERS = [
    "ECDHE-ECDSA-AES256-GCM-SHA384",
    "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-CHACHA20-POLY1305",
    "ECDHE-RSA-CHACHA20-POLY1305",
    "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-RSA-AES128-GCM-SHA256",
]


@dataclass
class TLSConfig:
    """
    TLS configuration settings.

    Attributes:
        min_version: Minimum TLS version (1.2 or 1.3)
        require_tls13: Require TLS 1.3 only
        cert_file: Path to certificate file
        key_file: Path to private key file
        ca_file: Path to CA bundle
        verify_client: Require client certificates (mTLS)
        verify_hostname: Verify server hostname
        check_revocation: Check certificate revocation (OCSP/CRL)
        pinned_certs: Certificate fingerprints for pinning
    """
    min_version: str = "1.2"
    require_tls13: bool = False
    cert_file: Optional[Path] = None
    key_file: Optional[Path] = None
    ca_file: Optional[Path] = None
    verify_client: bool = False
    verify_hostname: bool = True
    check_revocation: bool = True
    pinned_certs: List[str] = field(default_factory=list)
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 year

    def create_ssl_context(self, purpose: str = "client") -> ssl.SSLContext:
        """
        Create an SSL context with secure settings.

        Args:
            purpose: "client" or "server"

        Returns:
            Configured SSLContext
        """
        # Choose purpose
        if purpose == "server":
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        else:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        # Set minimum version
        if self.require_tls13:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        elif self.min_version == "1.3":
            ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        else:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2

        # Set maximum version (latest)
        ctx.maximum_version = ssl.TLSVersion.TLSv1_3

        # Set cipher suites
        if not self.require_tls13:
            cipher_string = ":".join(TLS12_CIPHERS)
            ctx.set_ciphers(cipher_string)

        # Load certificates
        if self.cert_file and self.key_file:
            ctx.load_cert_chain(
                certfile=str(self.cert_file),
                keyfile=str(self.key_file),
            )

        # Load CA bundle
        if self.ca_file:
            ctx.load_verify_locations(cafile=str(self.ca_file))
        else:
            ctx.load_default_certs()

        # Client verification
        if purpose == "server" and self.verify_client:
            ctx.verify_mode = ssl.CERT_REQUIRED
        elif purpose == "client":
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.check_hostname = self.verify_hostname
        else:
            ctx.verify_mode = ssl.CERT_NONE

        # Security options
        ctx.options |= ssl.OP_NO_SSLv2
        ctx.options |= ssl.OP_NO_SSLv3
        ctx.options |= ssl.OP_NO_TLSv1
        ctx.options |= ssl.OP_NO_TLSv1_1
        ctx.options |= ssl.OP_NO_COMPRESSION  # Disable compression (CRIME)
        ctx.options |= ssl.OP_SINGLE_DH_USE
        ctx.options |= ssl.OP_SINGLE_ECDH_USE

        return ctx

    def get_hsts_header(self) -> str:
        """Get HSTS header value."""
        if not self.hsts_enabled:
            return ""
        return f"max-age={self.hsts_max_age}; includeSubDomains; preload"


@dataclass
class Certificate:
    """
    Certificate information.

    Attributes:
        subject: Certificate subject
        issuer: Certificate issuer
        serial_number: Serial number
        not_before: Valid from
        not_after: Valid until
        fingerprint_sha256: SHA-256 fingerprint
        san: Subject alternative names
        is_ca: Whether this is a CA certificate
    """
    subject: Dict[str, str]
    issuer: Dict[str, str]
    serial_number: str
    not_before: datetime
    not_after: datetime
    fingerprint_sha256: str
    san: List[str] = field(default_factory=list)
    is_ca: bool = False

    @property
    def is_expired(self) -> bool:
        """Check if certificate is expired."""
        return datetime.utcnow() > self.not_after

    @property
    def is_not_yet_valid(self) -> bool:
        """Check if certificate is not yet valid."""
        return datetime.utcnow() < self.not_before

    @property
    def is_valid(self) -> bool:
        """Check if certificate is currently valid."""
        now = datetime.utcnow()
        return self.not_before <= now <= self.not_after

    @property
    def days_until_expiry(self) -> int:
        """Get days until certificate expires."""
        delta = self.not_after - datetime.utcnow()
        return max(0, delta.days)

    @property
    def needs_renewal(self) -> bool:
        """Check if certificate should be renewed (< 30 days)."""
        return self.days_until_expiry < 30

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "subject": self.subject,
            "issuer": self.issuer,
            "serial_number": self.serial_number,
            "not_before": self.not_before.isoformat(),
            "not_after": self.not_after.isoformat(),
            "fingerprint_sha256": self.fingerprint_sha256,
            "san": self.san,
            "is_ca": self.is_ca,
            "is_valid": self.is_valid,
            "days_until_expiry": self.days_until_expiry,
        }


class CertificateManager:
    """
    Certificate management service.

    Handles certificate generation, renewal, and validation.
    """

    def __init__(
        self,
        cert_dir: Path,
        ca_cert: Optional[Path] = None,
        ca_key: Optional[Path] = None,
    ):
        """
        Initialize certificate manager.

        Args:
            cert_dir: Directory for certificate storage
            ca_cert: Path to CA certificate (for signing)
            ca_key: Path to CA private key
        """
        self._cert_dir = Path(cert_dir)
        self._cert_dir.mkdir(parents=True, exist_ok=True)
        self._ca_cert = ca_cert
        self._ca_key = ca_key

        # Set restrictive permissions
        try:
            os.chmod(self._cert_dir, 0o700)
        except OSError:
            pass

    async def generate_self_signed(
        self,
        common_name: str,
        san: Optional[List[str]] = None,
        days: int = 365,
        key_size: int = 4096,
        output_prefix: str = "server",
    ) -> Tuple[Path, Path]:
        """
        Generate a self-signed certificate.

        Args:
            common_name: Certificate common name
            san: Subject alternative names
            days: Validity period in days
            key_size: RSA key size
            output_prefix: Output filename prefix

        Returns:
            Tuple of (cert_path, key_path)
        """
        cert_path = self._cert_dir / f"{output_prefix}.crt"
        key_path = self._cert_dir / f"{output_prefix}.key"

        # Build openssl command
        san_config = ""
        if san:
            san_entries = [f"DNS:{name}" if not name.startswith(("IP:", "DNS:")) else name for name in san]
            san_entries.append(f"DNS:{common_name}")
            san_config = ",".join(san_entries)

        # Create config file for SAN support
        config_path = self._cert_dir / f"{output_prefix}_openssl.cnf"
        config_content = f"""
[req]
default_bits = {key_size}
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
CN = {common_name}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
"""
        if san_config:
            config_content += f"subjectAltName = {san_config}\n"

        config_path.write_text(config_content)

        try:
            # Generate key and certificate
            process = await asyncio.create_subprocess_exec(
                "openssl", "req", "-x509", "-nodes",
                "-days", str(days),
                "-newkey", f"rsa:{key_size}",
                "-keyout", str(key_path),
                "-out", str(cert_path),
                "-config", str(config_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"OpenSSL error: {stderr.decode()}")

            # Set restrictive permissions on key
            os.chmod(key_path, 0o600)

            logger.info(f"Generated self-signed certificate: {cert_path}")

            return cert_path, key_path

        finally:
            # Clean up config
            if config_path.exists():
                config_path.unlink()

    async def generate_csr(
        self,
        common_name: str,
        san: Optional[List[str]] = None,
        key_size: int = 4096,
        output_prefix: str = "server",
    ) -> Tuple[Path, Path]:
        """
        Generate a Certificate Signing Request (CSR).

        Args:
            common_name: Certificate common name
            san: Subject alternative names
            key_size: RSA key size
            output_prefix: Output filename prefix

        Returns:
            Tuple of (csr_path, key_path)
        """
        csr_path = self._cert_dir / f"{output_prefix}.csr"
        key_path = self._cert_dir / f"{output_prefix}.key"

        # Create config for SAN
        config_path = self._cert_dir / f"{output_prefix}_csr.cnf"
        config_content = f"""
[req]
default_bits = {key_size}
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
CN = {common_name}

[req_ext]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
"""
        if san:
            san_entries = [f"DNS:{name}" if not name.startswith(("IP:", "DNS:")) else name for name in san]
            san_entries.append(f"DNS:{common_name}")
            config_content += f"subjectAltName = {','.join(san_entries)}\n"

        config_path.write_text(config_content)

        try:
            # Generate key and CSR
            process = await asyncio.create_subprocess_exec(
                "openssl", "req", "-new", "-nodes",
                "-newkey", f"rsa:{key_size}",
                "-keyout", str(key_path),
                "-out", str(csr_path),
                "-config", str(config_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"OpenSSL error: {stderr.decode()}")

            os.chmod(key_path, 0o600)

            logger.info(f"Generated CSR: {csr_path}")

            return csr_path, key_path

        finally:
            if config_path.exists():
                config_path.unlink()

    async def sign_csr(
        self,
        csr_path: Path,
        days: int = 365,
        output_name: Optional[str] = None,
    ) -> Path:
        """
        Sign a CSR with the CA certificate.

        Args:
            csr_path: Path to CSR
            days: Validity period
            output_name: Output certificate name

        Returns:
            Path to signed certificate
        """
        if not self._ca_cert or not self._ca_key:
            raise RuntimeError("CA certificate and key required for signing")

        if output_name is None:
            output_name = csr_path.stem + ".crt"

        cert_path = self._cert_dir / output_name

        process = await asyncio.create_subprocess_exec(
            "openssl", "x509", "-req",
            "-in", str(csr_path),
            "-CA", str(self._ca_cert),
            "-CAkey", str(self._ca_key),
            "-CAcreateserial",
            "-out", str(cert_path),
            "-days", str(days),
            "-sha256",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Signing error: {stderr.decode()}")

        logger.info(f"Signed certificate: {cert_path}")

        return cert_path

    async def get_certificate_info(self, cert_path: Path) -> Certificate:
        """
        Get certificate information.

        Args:
            cert_path: Path to certificate

        Returns:
            Certificate information
        """
        # Get certificate details using openssl
        process = await asyncio.create_subprocess_exec(
            "openssl", "x509", "-in", str(cert_path),
            "-noout", "-text", "-fingerprint", "-sha256",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Certificate read error: {stderr.decode()}")

        output = stdout.decode()

        # Parse output
        cert = Certificate(
            subject=self._parse_dn(output, "Subject:"),
            issuer=self._parse_dn(output, "Issuer:"),
            serial_number=self._parse_field(output, "Serial Number:"),
            not_before=self._parse_date(output, "Not Before:"),
            not_after=self._parse_date(output, "Not After :"),
            fingerprint_sha256=self._parse_fingerprint(output),
            san=self._parse_san(output),
            is_ca="CA:TRUE" in output,
        )

        return cert

    def _parse_dn(self, output: str, field: str) -> Dict[str, str]:
        """Parse distinguished name from openssl output."""
        result = {}
        for line in output.split('\n'):
            if field in line:
                dn_str = line.split(field, 1)[1].strip()
                for part in dn_str.split(','):
                    part = part.strip()
                    if '=' in part:
                        key, value = part.split('=', 1)
                        result[key.strip()] = value.strip()
        return result

    def _parse_field(self, output: str, field: str) -> str:
        """Parse a simple field from openssl output."""
        for line in output.split('\n'):
            if field in line:
                return line.split(':', 1)[1].strip()
        return ""

    def _parse_date(self, output: str, field: str) -> datetime:
        """Parse a date field from openssl output."""
        date_str = self._parse_field(output, field)
        try:
            # Format: "Dec 15 10:30:00 2025 GMT"
            return datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
        except ValueError:
            return datetime.utcnow()

    def _parse_fingerprint(self, output: str) -> str:
        """Parse SHA-256 fingerprint from openssl output."""
        for line in output.split('\n'):
            if "sha256 Fingerprint" in line.lower():
                return line.split('=', 1)[1].strip().replace(':', '')
        return ""

    def _parse_san(self, output: str) -> List[str]:
        """Parse Subject Alternative Names."""
        san = []
        in_san = False
        for line in output.split('\n'):
            if "Subject Alternative Name:" in line:
                in_san = True
                continue
            if in_san:
                if line.strip().startswith("DNS:") or line.strip().startswith("IP:"):
                    parts = line.strip().split(',')
                    for part in parts:
                        part = part.strip()
                        if part.startswith("DNS:"):
                            san.append(part[4:])
                        elif part.startswith("IP:"):
                            san.append(part)
                break
        return san

    async def verify_certificate(
        self,
        cert_path: Path,
        ca_bundle: Optional[Path] = None,
        check_revocation: bool = True,
    ) -> Tuple[bool, List[str]]:
        """
        Verify a certificate.

        Args:
            cert_path: Certificate to verify
            ca_bundle: CA bundle for verification
            check_revocation: Check certificate revocation

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []

        # Get certificate info
        try:
            cert = await self.get_certificate_info(cert_path)
        except Exception as e:
            return False, [f"Cannot read certificate: {e}"]

        # Check validity period
        if cert.is_expired:
            issues.append(f"Certificate expired on {cert.not_after}")
        elif cert.is_not_yet_valid:
            issues.append(f"Certificate not valid until {cert.not_before}")

        # Check if renewal needed
        if cert.needs_renewal:
            issues.append(f"Certificate expires in {cert.days_until_expiry} days")

        # Verify chain if CA bundle provided
        if ca_bundle:
            args = ["openssl", "verify"]
            if ca_bundle:
                args.extend(["-CAfile", str(ca_bundle)])
            args.append(str(cert_path))

            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                issues.append(f"Chain verification failed: {stderr.decode()}")

        # Check revocation (OCSP)
        if check_revocation and not cert.is_ca:
            revoked = await self._check_ocsp(cert_path)
            if revoked:
                issues.append("Certificate has been revoked")

        return len(issues) == 0, issues

    async def _check_ocsp(self, cert_path: Path) -> bool:
        """Check certificate revocation via OCSP."""
        # This is a simplified check - full implementation would extract
        # OCSP responder URL from certificate and query it
        try:
            process = await asyncio.create_subprocess_exec(
                "openssl", "x509", "-in", str(cert_path),
                "-noout", "-ocsp_uri",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            ocsp_uri = stdout.decode().strip()

            if not ocsp_uri:
                return False  # No OCSP, assume not revoked

            # Would perform OCSP check here
            # For now, return False (not revoked)
            return False

        except Exception:
            return False

    async def renew_certificate(
        self,
        cert_path: Path,
        key_path: Path,
        days: int = 365,
    ) -> Tuple[Path, Path]:
        """
        Renew a certificate by generating a new one.

        Args:
            cert_path: Current certificate
            key_path: Current private key
            days: New validity period

        Returns:
            Tuple of (new_cert_path, new_key_path)
        """
        # Get current certificate info
        cert = await self.get_certificate_info(cert_path)

        cn = cert.subject.get("CN", "localhost")
        san = cert.san

        # Generate new certificate
        prefix = cert_path.stem + "_renewed"

        if self._ca_cert and self._ca_key:
            # Generate CSR and sign with CA
            csr_path, new_key_path = await self.generate_csr(
                common_name=cn,
                san=san,
                output_prefix=prefix,
            )
            new_cert_path = await self.sign_csr(csr_path, days)
            csr_path.unlink()  # Clean up CSR
        else:
            # Generate self-signed
            new_cert_path, new_key_path = await self.generate_self_signed(
                common_name=cn,
                san=san,
                days=days,
                output_prefix=prefix,
            )

        logger.info(f"Certificate renewed: {new_cert_path}")

        return new_cert_path, new_key_path

    def list_certificates(self) -> List[Path]:
        """List all certificates in the certificate directory."""
        return list(self._cert_dir.glob("*.crt")) + list(self._cert_dir.glob("*.pem"))

    async def get_expiring_certificates(
        self,
        days_threshold: int = 30,
    ) -> List[Tuple[Path, Certificate]]:
        """
        Get certificates expiring within threshold.

        Args:
            days_threshold: Days until expiry threshold

        Returns:
            List of (path, certificate) tuples
        """
        expiring = []

        for cert_path in self.list_certificates():
            try:
                cert = await self.get_certificate_info(cert_path)
                if cert.days_until_expiry <= days_threshold:
                    expiring.append((cert_path, cert))
            except Exception as e:
                logger.warning(f"Error reading certificate {cert_path}: {e}")

        return sorted(expiring, key=lambda x: x[1].days_until_expiry)


def create_tls_config(config: Dict[str, Any]) -> TLSConfig:
    """
    Create TLS configuration from dictionary.

    Args:
        config: TLS configuration dictionary

    Returns:
        TLSConfig instance
    """
    return TLSConfig(
        min_version=config.get("min_version", "1.2"),
        require_tls13=config.get("require_tls13", False),
        cert_file=Path(config["cert_file"]) if config.get("cert_file") else None,
        key_file=Path(config["key_file"]) if config.get("key_file") else None,
        ca_file=Path(config["ca_file"]) if config.get("ca_file") else None,
        verify_client=config.get("verify_client", False),
        verify_hostname=config.get("verify_hostname", True),
        check_revocation=config.get("check_revocation", True),
        pinned_certs=config.get("pinned_certs", []),
        hsts_enabled=config.get("hsts_enabled", True),
        hsts_max_age=config.get("hsts_max_age", 31536000),
    )
