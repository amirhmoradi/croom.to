"""
OS Support and Rollback for Croom.

Provides:
- Trixie (Debian 13) OS support
- Version rollback capabilities
- Legacy image migration
- OS compatibility detection
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OSType(Enum):
    """Supported operating systems."""
    RASPBERRY_PI_OS = "raspbian"
    DEBIAN = "debian"
    UBUNTU = "ubuntu"
    UNKNOWN = "unknown"


class OSRelease(Enum):
    """Supported OS releases."""
    BULLSEYE = "bullseye"       # Debian 11
    BOOKWORM = "bookworm"       # Debian 12
    TRIXIE = "trixie"           # Debian 13 (testing/unstable)
    JAMMY = "jammy"             # Ubuntu 22.04
    NOBLE = "noble"             # Ubuntu 24.04
    UNKNOWN = "unknown"


class Architecture(Enum):
    """Supported architectures."""
    ARM64 = "aarch64"
    ARMHF = "armv7l"
    AMD64 = "x86_64"
    UNKNOWN = "unknown"


@dataclass
class OSInfo:
    """Operating system information."""
    os_type: OSType
    release: OSRelease
    version: str
    codename: str
    architecture: Architecture
    kernel_version: str
    is_raspberry_pi: bool = False
    pi_model: str = ""

    def to_dict(self) -> dict:
        return {
            "os_type": self.os_type.value,
            "release": self.release.value,
            "version": self.version,
            "codename": self.codename,
            "architecture": self.architecture.value,
            "kernel_version": self.kernel_version,
            "is_raspberry_pi": self.is_raspberry_pi,
            "pi_model": self.pi_model,
        }


@dataclass
class VersionSnapshot:
    """Snapshot of installed version for rollback."""
    id: str
    timestamp: datetime
    version: str
    packages: Dict[str, str]  # package -> version
    config_backup: str  # Path to config backup
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "packages": self.packages,
            "config_backup": self.config_backup,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VersionSnapshot":
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            version=data["version"],
            packages=data["packages"],
            config_backup=data["config_backup"],
            description=data.get("description", ""),
        )


class OSDetector:
    """
    Detects operating system information.
    """

    def detect(self) -> OSInfo:
        """Detect current OS information."""
        os_type = OSType.UNKNOWN
        release = OSRelease.UNKNOWN
        version = ""
        codename = ""

        # Read /etc/os-release
        os_release = self._read_os_release()

        # Determine OS type
        os_id = os_release.get("ID", "").lower()
        if os_id in ["raspbian", "raspberry"]:
            os_type = OSType.RASPBERRY_PI_OS
        elif os_id == "debian":
            os_type = OSType.DEBIAN
        elif os_id == "ubuntu":
            os_type = OSType.UBUNTU

        # Determine release
        version_codename = os_release.get("VERSION_CODENAME", "").lower()
        version = os_release.get("VERSION_ID", "")

        release_map = {
            "bullseye": OSRelease.BULLSEYE,
            "bookworm": OSRelease.BOOKWORM,
            "trixie": OSRelease.TRIXIE,
            "jammy": OSRelease.JAMMY,
            "noble": OSRelease.NOBLE,
        }
        release = release_map.get(version_codename, OSRelease.UNKNOWN)
        codename = version_codename

        # Detect architecture
        arch = self._detect_architecture()

        # Detect Raspberry Pi
        is_pi, pi_model = self._detect_raspberry_pi()

        # Get kernel version
        kernel = os.uname().release

        return OSInfo(
            os_type=os_type,
            release=release,
            version=version,
            codename=codename,
            architecture=arch,
            kernel_version=kernel,
            is_raspberry_pi=is_pi,
            pi_model=pi_model,
        )

    def _read_os_release(self) -> Dict[str, str]:
        """Read /etc/os-release file."""
        os_release = {}

        try:
            with open("/etc/os-release") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os_release[key] = value.strip('"')
        except Exception:
            pass

        return os_release

    def _detect_architecture(self) -> Architecture:
        """Detect system architecture."""
        machine = os.uname().machine

        arch_map = {
            "aarch64": Architecture.ARM64,
            "arm64": Architecture.ARM64,
            "armv7l": Architecture.ARMHF,
            "x86_64": Architecture.AMD64,
            "amd64": Architecture.AMD64,
        }

        return arch_map.get(machine, Architecture.UNKNOWN)

    def _detect_raspberry_pi(self) -> Tuple[bool, str]:
        """Detect if running on Raspberry Pi and model."""
        try:
            with open("/proc/device-tree/model") as f:
                model = f.read().strip().rstrip('\x00')
                if "Raspberry Pi" in model:
                    return True, model
        except Exception:
            pass

        # Fallback: check cpuinfo
        try:
            with open("/proc/cpuinfo") as f:
                content = f.read()
                if "BCM" in content:
                    return True, "Raspberry Pi"
        except Exception:
            pass

        return False, ""


class TrixieSupport:
    """
    Debian Trixie (13) specific support.

    Handles:
    - Package compatibility
    - Dependency resolution
    - Feature detection
    """

    # Packages that need different versions on Trixie
    TRIXIE_PACKAGE_OVERRIDES = {
        "python3": "python3 (>= 3.11)",
        "chromium-browser": "chromium",
        "libqt5-*": "libqt6-*",
    }

    # Features available on Trixie
    TRIXIE_FEATURES = {
        "python311": True,
        "qt6": True,
        "wayland_default": True,
        "pipewire": True,
    }

    def __init__(self):
        self._detector = OSDetector()
        self._os_info = None

    def is_trixie(self) -> bool:
        """Check if running on Trixie."""
        if not self._os_info:
            self._os_info = self._detector.detect()
        return self._os_info.release == OSRelease.TRIXIE

    def get_package_name(self, package: str) -> str:
        """Get Trixie-compatible package name."""
        if not self.is_trixie():
            return package

        return self.TRIXIE_PACKAGE_OVERRIDES.get(package, package)

    def has_feature(self, feature: str) -> bool:
        """Check if Trixie feature is available."""
        if not self.is_trixie():
            return False
        return self.TRIXIE_FEATURES.get(feature, False)

    def get_compatibility_warnings(self) -> List[str]:
        """Get Trixie compatibility warnings."""
        warnings = []

        if not self.is_trixie():
            return warnings

        # Check for known issues
        if self._check_wayland_session():
            warnings.append(
                "Wayland session detected. Some features may behave differently."
            )

        if not self._check_qt6_available():
            warnings.append(
                "Qt6 not installed. UI may fall back to Qt5."
            )

        return warnings

    def _check_wayland_session(self) -> bool:
        """Check if running under Wayland."""
        return os.environ.get("XDG_SESSION_TYPE") == "wayland"

    def _check_qt6_available(self) -> bool:
        """Check if Qt6 is available."""
        try:
            result = subprocess.run(
                ["dpkg", "-l", "libqt6core6"],
                capture_output=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    async def apply_trixie_fixes(self) -> None:
        """Apply Trixie-specific fixes."""
        if not self.is_trixie():
            return

        # Fix for chromium package name change
        chromium_link = Path("/usr/bin/chromium-browser")
        if not chromium_link.exists():
            chromium = Path("/usr/bin/chromium")
            if chromium.exists():
                chromium_link.symlink_to(chromium)

        logger.info("Applied Trixie compatibility fixes")


class RollbackService:
    """
    Version rollback service for Croom.

    Manages snapshots and enables reverting to previous versions.
    """

    def __init__(
        self,
        snapshot_dir: str = "/var/lib/croom/snapshots",
        max_snapshots: int = 5,
    ):
        self._snapshot_dir = Path(snapshot_dir)
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._max_snapshots = max_snapshots

        self._snapshots: List[VersionSnapshot] = []
        self._load_snapshots()

    def _load_snapshots(self) -> None:
        """Load existing snapshots."""
        manifest_file = self._snapshot_dir / "manifest.json"

        if manifest_file.exists():
            try:
                with open(manifest_file) as f:
                    data = json.load(f)
                    self._snapshots = [
                        VersionSnapshot.from_dict(s)
                        for s in data.get("snapshots", [])
                    ]
            except Exception as e:
                logger.error(f"Failed to load snapshots: {e}")

    def _save_manifest(self) -> None:
        """Save snapshot manifest."""
        manifest_file = self._snapshot_dir / "manifest.json"

        data = {
            "snapshots": [s.to_dict() for s in self._snapshots],
        }

        with open(manifest_file, "w") as f:
            json.dump(data, f, indent=2)

    async def create_snapshot(
        self,
        description: str = "",
    ) -> Optional[VersionSnapshot]:
        """Create a snapshot of current installation."""
        import uuid

        snapshot_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow()

        # Get installed package versions
        packages = await self._get_installed_packages()

        # Get current version
        version = packages.get("croom", "unknown")

        # Backup configuration
        config_backup = await self._backup_config(snapshot_id)

        snapshot = VersionSnapshot(
            id=snapshot_id,
            timestamp=timestamp,
            version=version,
            packages=packages,
            config_backup=config_backup,
            description=description or f"Snapshot before update to {version}",
        )

        self._snapshots.append(snapshot)

        # Enforce max snapshots
        while len(self._snapshots) > self._max_snapshots:
            old = self._snapshots.pop(0)
            await self._cleanup_snapshot(old)

        self._save_manifest()

        logger.info(f"Created snapshot: {snapshot_id}")
        return snapshot

    async def rollback(self, snapshot_id: str) -> bool:
        """Rollback to a specific snapshot."""
        snapshot = next(
            (s for s in self._snapshots if s.id == snapshot_id),
            None
        )

        if not snapshot:
            logger.error(f"Snapshot not found: {snapshot_id}")
            return False

        logger.info(f"Rolling back to snapshot: {snapshot_id}")

        try:
            # Install specific package versions
            for package, version in snapshot.packages.items():
                if package.startswith("croom"):
                    await self._install_version(package, version)

            # Restore configuration
            await self._restore_config(snapshot.config_backup)

            logger.info(f"Rollback complete: {snapshot_id}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    async def get_snapshots(self) -> List[VersionSnapshot]:
        """Get list of available snapshots."""
        return self._snapshots.copy()

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        snapshot = next(
            (s for s in self._snapshots if s.id == snapshot_id),
            None
        )

        if not snapshot:
            return False

        await self._cleanup_snapshot(snapshot)
        self._snapshots.remove(snapshot)
        self._save_manifest()

        logger.info(f"Deleted snapshot: {snapshot_id}")
        return True

    async def _get_installed_packages(self) -> Dict[str, str]:
        """Get installed Croom package versions."""
        packages = {}

        try:
            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Package} ${Version}\n", "croom*"],
                capture_output=True,
                text=True,
            )

            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2:
                    packages[parts[0]] = parts[1]

        except Exception as e:
            logger.error(f"Failed to get installed packages: {e}")

        return packages

    async def _backup_config(self, snapshot_id: str) -> str:
        """Backup configuration files."""
        backup_dir = self._snapshot_dir / snapshot_id / "config"
        backup_dir.mkdir(parents=True, exist_ok=True)

        config_dir = Path("/etc/croom")
        if config_dir.exists():
            shutil.copytree(config_dir, backup_dir / "croom", dirs_exist_ok=True)

        return str(backup_dir)

    async def _restore_config(self, backup_path: str) -> None:
        """Restore configuration from backup."""
        backup_dir = Path(backup_path)

        if not backup_dir.exists():
            logger.warning(f"Config backup not found: {backup_path}")
            return

        croom_config = backup_dir / "croom"
        if croom_config.exists():
            shutil.copytree(croom_config, "/etc/croom", dirs_exist_ok=True)

    async def _install_version(self, package: str, version: str) -> None:
        """Install specific package version."""
        subprocess.run(
            ["apt", "install", "-y", "--allow-downgrades", f"{package}={version}"],
            check=True,
        )

    async def _cleanup_snapshot(self, snapshot: VersionSnapshot) -> None:
        """Cleanup snapshot files."""
        snapshot_dir = self._snapshot_dir / snapshot.id

        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)


class LegacyMigration:
    """
    Migration tool for legacy Croom image-based installations.

    Converts image-based installations to package-based.
    """

    # Known legacy installation paths
    LEGACY_PATHS = {
        "config": "/home/pi/.croom",
        "app": "/opt/croom",
        "service": "/etc/systemd/system/croom.service",
        "data": "/var/lib/croom",
    }

    def __init__(self):
        self._legacy_detected = False
        self._legacy_version = None
        self._migration_log: List[str] = []

    async def detect_legacy(self) -> bool:
        """Detect legacy installation."""
        # Check for legacy installation markers
        legacy_markers = [
            Path(self.LEGACY_PATHS["config"]),
            Path(self.LEGACY_PATHS["app"]),
            Path("/home/pi/.croom/version"),
        ]

        self._legacy_detected = any(p.exists() for p in legacy_markers)

        if self._legacy_detected:
            # Try to get version
            version_file = Path("/home/pi/.croom/version")
            if version_file.exists():
                self._legacy_version = version_file.read_text().strip()

            logger.info(f"Legacy installation detected: {self._legacy_version or 'unknown version'}")

        return self._legacy_detected

    async def migrate(
        self,
        backup: bool = True,
        cleanup: bool = False,
        progress_callback: Callable[[str, int], None] = None,
    ) -> bool:
        """
        Migrate from legacy to package-based installation.

        Args:
            backup: Create backup of legacy installation
            cleanup: Remove legacy files after migration
            progress_callback: Callback for progress updates (message, percent)

        Returns:
            True if migration successful
        """
        if not self._legacy_detected:
            if not await self.detect_legacy():
                logger.info("No legacy installation to migrate")
                return True

        self._migration_log = []

        try:
            # Step 1: Create backup (10%)
            if progress_callback:
                progress_callback("Creating backup...", 10)

            if backup:
                await self._create_backup()

            # Step 2: Stop legacy services (20%)
            if progress_callback:
                progress_callback("Stopping services...", 20)

            await self._stop_legacy_services()

            # Step 3: Migrate configuration (40%)
            if progress_callback:
                progress_callback("Migrating configuration...", 40)

            await self._migrate_config()

            # Step 4: Migrate data (60%)
            if progress_callback:
                progress_callback("Migrating data...", 60)

            await self._migrate_data()

            # Step 5: Install packages (80%)
            if progress_callback:
                progress_callback("Installing packages...", 80)

            await self._install_packages()

            # Step 6: Cleanup (90%)
            if cleanup:
                if progress_callback:
                    progress_callback("Cleaning up...", 90)

                await self._cleanup_legacy()

            # Step 7: Start new services (100%)
            if progress_callback:
                progress_callback("Starting services...", 100)

            await self._start_services()

            logger.info("Migration completed successfully")
            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self._migration_log.append(f"ERROR: {e}")
            return False

    async def _create_backup(self) -> None:
        """Create backup of legacy installation."""
        backup_dir = Path(f"/var/backups/croom-legacy-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        backup_dir.mkdir(parents=True, exist_ok=True)

        for name, path in self.LEGACY_PATHS.items():
            src = Path(path)
            if src.exists():
                dest = backup_dir / name
                if src.is_dir():
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)

        self._migration_log.append(f"Backup created: {backup_dir}")
        logger.info(f"Legacy backup created: {backup_dir}")

    async def _stop_legacy_services(self) -> None:
        """Stop legacy services."""
        services = ["croom", "croom-ui", "croom-browser"]

        for service in services:
            try:
                subprocess.run(
                    ["systemctl", "stop", service],
                    capture_output=True,
                )
                subprocess.run(
                    ["systemctl", "disable", service],
                    capture_output=True,
                )
            except Exception:
                pass

        self._migration_log.append("Legacy services stopped")

    async def _migrate_config(self) -> None:
        """Migrate configuration from legacy location."""
        legacy_config = Path(self.LEGACY_PATHS["config"])
        new_config = Path("/etc/croom")

        if not legacy_config.exists():
            return

        new_config.mkdir(parents=True, exist_ok=True)

        # Migrate known config files
        config_files = [
            ("config.json", "croom.conf"),
            ("calendar.json", "calendar.conf"),
            ("network.json", "network.conf"),
        ]

        for old_name, new_name in config_files:
            old_path = legacy_config / old_name
            new_path = new_config / new_name

            if old_path.exists():
                # Convert JSON to new format if needed
                await self._convert_config(old_path, new_path)

        self._migration_log.append("Configuration migrated")

    async def _convert_config(self, old_path: Path, new_path: Path) -> None:
        """Convert legacy config to new format."""
        try:
            with open(old_path) as f:
                old_config = json.load(f)

            # Transform config as needed
            new_config = self._transform_config(old_config)

            with open(new_path, "w") as f:
                json.dump(new_config, f, indent=2)

        except Exception as e:
            logger.warning(f"Config conversion warning: {e}")
            # Just copy as-is
            shutil.copy2(old_path, new_path)

    def _transform_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform legacy config format to new format."""
        # Map old keys to new keys
        key_mapping = {
            "room_name": "device_name",
            "display_name": "device_name",
            "meet_email": "calendar_email",
            "meet_password": "calendar_credentials",
        }

        new_config = {}

        for old_key, value in config.items():
            new_key = key_mapping.get(old_key, old_key)
            new_config[new_key] = value

        return new_config

    async def _migrate_data(self) -> None:
        """Migrate data files."""
        legacy_data = Path(self.LEGACY_PATHS["data"])
        new_data = Path("/var/lib/croom")

        if legacy_data.exists():
            new_data.mkdir(parents=True, exist_ok=True)
            shutil.copytree(legacy_data, new_data, dirs_exist_ok=True)

        self._migration_log.append("Data migrated")

    async def _install_packages(self) -> None:
        """Install Croom packages."""
        subprocess.run(["apt", "update"], check=True)
        subprocess.run(["apt", "install", "-y", "croom"], check=True)

        self._migration_log.append("Packages installed")

    async def _cleanup_legacy(self) -> None:
        """Remove legacy installation files."""
        for name, path in self.LEGACY_PATHS.items():
            p = Path(path)
            if p.exists():
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()

        # Remove legacy service files
        for service_file in Path("/etc/systemd/system").glob("croom*.service"):
            service_file.unlink()

        subprocess.run(["systemctl", "daemon-reload"], check=True)

        self._migration_log.append("Legacy files cleaned up")

    async def _start_services(self) -> None:
        """Start new Croom services."""
        subprocess.run(["systemctl", "enable", "croom"], check=True)
        subprocess.run(["systemctl", "start", "croom"], check=True)

        self._migration_log.append("Services started")

    def get_migration_log(self) -> List[str]:
        """Get migration log."""
        return self._migration_log.copy()
