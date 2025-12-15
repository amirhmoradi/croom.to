"""
APT Package Repository and Update System for PiMeet.

Provides Debian packaging infrastructure including:
- Package repository management
- APT repository configuration
- Automatic updates via apt
- Package signing
- Version management
"""

import asyncio
import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class PackageType(Enum):
    """Package types."""
    CORE = "pimeet-core"
    UI = "pimeet-ui"
    AI = "pimeet-ai"
    DASHBOARD = "pimeet-dashboard"
    MEETING = "pimeet-meeting"
    FULL = "pimeet"  # Meta-package


class Architecture(Enum):
    """Supported architectures."""
    ARM64 = "arm64"
    ARMHF = "armhf"
    AMD64 = "amd64"
    ALL = "all"


class Distribution(Enum):
    """Supported distributions."""
    BOOKWORM = "bookworm"
    TRIXIE = "trixie"
    BULLSEYE = "bullseye"


@dataclass
class PackageInfo:
    """Debian package information."""
    name: str
    version: str
    architecture: Architecture
    distribution: Distribution
    description: str
    maintainer: str = "PiMeet Team <team@pimeet.io>"
    homepage: str = "https://pimeet.io"
    section: str = "misc"
    priority: str = "optional"
    depends: List[str] = field(default_factory=list)
    recommends: List[str] = field(default_factory=list)
    suggests: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    replaces: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    pre_depends: List[str] = field(default_factory=list)
    installed_size: int = 0
    file_path: Optional[str] = None

    def get_control_content(self) -> str:
        """Generate debian/control file content."""
        lines = [
            f"Package: {self.name}",
            f"Version: {self.version}",
            f"Architecture: {self.architecture.value}",
            f"Maintainer: {self.maintainer}",
            f"Description: {self.description}",
            f"Homepage: {self.homepage}",
            f"Section: {self.section}",
            f"Priority: {self.priority}",
        ]

        if self.installed_size > 0:
            lines.append(f"Installed-Size: {self.installed_size}")

        if self.pre_depends:
            lines.append(f"Pre-Depends: {', '.join(self.pre_depends)}")

        if self.depends:
            lines.append(f"Depends: {', '.join(self.depends)}")

        if self.recommends:
            lines.append(f"Recommends: {', '.join(self.recommends)}")

        if self.suggests:
            lines.append(f"Suggests: {', '.join(self.suggests)}")

        if self.conflicts:
            lines.append(f"Conflicts: {', '.join(self.conflicts)}")

        if self.replaces:
            lines.append(f"Replaces: {', '.join(self.replaces)}")

        if self.provides:
            lines.append(f"Provides: {', '.join(self.provides)}")

        return "\n".join(lines)


# Package definitions
PACKAGE_DEFINITIONS = {
    PackageType.CORE: PackageInfo(
        name="pimeet-core",
        version="1.0.0",
        architecture=Architecture.ALL,
        distribution=Distribution.BOOKWORM,
        description="PiMeet Core - Base conference room system",
        depends=[
            "python3 (>= 3.9)",
            "python3-pip",
            "python3-venv",
            "chromium-browser",
        ],
        recommends=["pimeet-ui", "pimeet-meeting"],
    ),
    PackageType.UI: PackageInfo(
        name="pimeet-ui",
        version="1.0.0",
        architecture=Architecture.ARM64,
        distribution=Distribution.BOOKWORM,
        description="PiMeet Touch UI - QML-based touch interface",
        depends=[
            "pimeet-core",
            "qml-module-qtquick2",
            "qml-module-qtquick-controls2",
            "qml-module-qtquick-layouts",
        ],
    ),
    PackageType.AI: PackageInfo(
        name="pimeet-ai",
        version="1.0.0",
        architecture=Architecture.ARM64,
        distribution=Distribution.BOOKWORM,
        description="PiMeet AI - Edge AI features for video conferencing",
        depends=[
            "pimeet-core",
            "python3-numpy",
            "python3-opencv",
        ],
        recommends=["hailo-firmware", "libedgetpu1-std"],
    ),
    PackageType.DASHBOARD: PackageInfo(
        name="pimeet-dashboard",
        version="1.0.0",
        architecture=Architecture.ALL,
        distribution=Distribution.BOOKWORM,
        description="PiMeet Dashboard Client - Remote management agent",
        depends=["pimeet-core"],
    ),
    PackageType.MEETING: PackageInfo(
        name="pimeet-meeting",
        version="1.0.0",
        architecture=Architecture.ALL,
        distribution=Distribution.BOOKWORM,
        description="PiMeet Meeting Providers - Google Meet, Teams, Zoom, Webex",
        depends=[
            "pimeet-core",
            "chromium-browser",
        ],
    ),
    PackageType.FULL: PackageInfo(
        name="pimeet",
        version="1.0.0",
        architecture=Architecture.ALL,
        distribution=Distribution.BOOKWORM,
        description="PiMeet - Complete conference room system",
        depends=[
            "pimeet-core",
            "pimeet-ui",
            "pimeet-meeting",
        ],
        recommends=[
            "pimeet-ai",
            "pimeet-dashboard",
        ],
    ),
}


class DebianPackageBuilder:
    """
    Builds Debian packages for PiMeet components.
    """

    def __init__(
        self,
        source_dir: str,
        output_dir: str,
        gpg_key: Optional[str] = None,
    ):
        self._source_dir = Path(source_dir)
        self._output_dir = Path(output_dir)
        self._gpg_key = gpg_key

        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def build_package(
        self,
        package_type: PackageType,
        version: str = None,
        architecture: Architecture = None,
        distribution: Distribution = None,
    ) -> Optional[str]:
        """Build a Debian package."""
        pkg_info = PACKAGE_DEFINITIONS.get(package_type)
        if not pkg_info:
            logger.error(f"Unknown package type: {package_type}")
            return None

        # Override version/arch/dist if provided
        if version:
            pkg_info.version = version
        if architecture:
            pkg_info.architecture = architecture
        if distribution:
            pkg_info.distribution = distribution

        logger.info(f"Building package: {pkg_info.name} {pkg_info.version}")

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                build_dir = Path(tmpdir) / pkg_info.name

                # Create package structure
                await self._create_package_structure(build_dir, pkg_info, package_type)

                # Build the package
                deb_file = await self._build_deb(build_dir, pkg_info)

                if deb_file:
                    # Move to output directory
                    output_file = self._output_dir / deb_file.name
                    shutil.move(str(deb_file), str(output_file))

                    # Sign if key provided
                    if self._gpg_key:
                        await self._sign_package(output_file)

                    logger.info(f"Package built: {output_file}")
                    return str(output_file)

        except Exception as e:
            logger.error(f"Failed to build package: {e}")
            return None

    async def _create_package_structure(
        self,
        build_dir: Path,
        pkg_info: PackageInfo,
        package_type: PackageType,
    ) -> None:
        """Create Debian package directory structure."""
        # Create directories
        debian_dir = build_dir / "DEBIAN"
        debian_dir.mkdir(parents=True)

        # Create control file
        control_file = debian_dir / "control"
        control_file.write_text(pkg_info.get_control_content())

        # Create installation directories based on package type
        if package_type == PackageType.CORE:
            await self._add_core_files(build_dir)
        elif package_type == PackageType.UI:
            await self._add_ui_files(build_dir)
        elif package_type == PackageType.AI:
            await self._add_ai_files(build_dir)
        elif package_type == PackageType.MEETING:
            await self._add_meeting_files(build_dir)
        elif package_type == PackageType.DASHBOARD:
            await self._add_dashboard_files(build_dir)

        # Create postinst script
        await self._create_postinst(build_dir, package_type)

        # Create prerm script
        await self._create_prerm(build_dir, package_type)

    async def _add_core_files(self, build_dir: Path) -> None:
        """Add core package files."""
        # Python package
        lib_dir = build_dir / "usr/lib/python3/dist-packages/pimeet"
        lib_dir.mkdir(parents=True)

        # Copy core modules
        core_modules = ["core", "services", "platform", "config"]
        for module in core_modules:
            src = self._source_dir / "src/pimeet" / module
            if src.exists():
                shutil.copytree(src, lib_dir / module)

        # Systemd service
        systemd_dir = build_dir / "lib/systemd/system"
        systemd_dir.mkdir(parents=True)

        service_content = """[Unit]
Description=PiMeet Conference Room System
After=network.target

[Service]
Type=simple
User=pimeet
ExecStart=/usr/bin/pimeet
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
        (systemd_dir / "pimeet.service").write_text(service_content)

        # Binary wrapper
        bin_dir = build_dir / "usr/bin"
        bin_dir.mkdir(parents=True)

        wrapper_content = """#!/bin/bash
exec python3 -m pimeet "$@"
"""
        wrapper_file = bin_dir / "pimeet"
        wrapper_file.write_text(wrapper_content)
        wrapper_file.chmod(0o755)

        # Configuration
        etc_dir = build_dir / "etc/pimeet"
        etc_dir.mkdir(parents=True)

    async def _add_ui_files(self, build_dir: Path) -> None:
        """Add UI package files."""
        # QML files
        share_dir = build_dir / "usr/share/pimeet/qml"
        share_dir.mkdir(parents=True)

        qml_src = self._source_dir / "src/pimeet-ui/qml"
        if qml_src.exists():
            shutil.copytree(qml_src, share_dir, dirs_exist_ok=True)

        # Python UI module
        lib_dir = build_dir / "usr/lib/python3/dist-packages/pimeet/ui"
        lib_dir.mkdir(parents=True)

        ui_src = self._source_dir / "src/pimeet/ui"
        if ui_src.exists():
            shutil.copytree(ui_src, lib_dir, dirs_exist_ok=True)

    async def _add_ai_files(self, build_dir: Path) -> None:
        """Add AI package files."""
        lib_dir = build_dir / "usr/lib/python3/dist-packages/pimeet/ai"
        lib_dir.mkdir(parents=True)

        ai_src = self._source_dir / "src/pimeet/ai"
        if ai_src.exists():
            shutil.copytree(ai_src, lib_dir, dirs_exist_ok=True)

        # Models directory
        models_dir = build_dir / "usr/share/pimeet/models"
        models_dir.mkdir(parents=True)

    async def _add_meeting_files(self, build_dir: Path) -> None:
        """Add meeting provider files."""
        lib_dir = build_dir / "usr/lib/python3/dist-packages/pimeet/meeting"
        lib_dir.mkdir(parents=True)

        meeting_src = self._source_dir / "src/pimeet/meeting"
        if meeting_src.exists():
            shutil.copytree(meeting_src, lib_dir, dirs_exist_ok=True)

    async def _add_dashboard_files(self, build_dir: Path) -> None:
        """Add dashboard client files."""
        lib_dir = build_dir / "usr/lib/python3/dist-packages/pimeet/dashboard"
        lib_dir.mkdir(parents=True)

        dashboard_src = self._source_dir / "src/pimeet/dashboard"
        if dashboard_src.exists():
            shutil.copytree(dashboard_src, lib_dir, dirs_exist_ok=True)

    async def _create_postinst(self, build_dir: Path, package_type: PackageType) -> None:
        """Create post-installation script."""
        postinst = build_dir / "DEBIAN/postinst"

        script = """#!/bin/bash
set -e

case "$1" in
    configure)
        # Create pimeet user if not exists
        if ! id -u pimeet > /dev/null 2>&1; then
            useradd -r -s /bin/false -d /var/lib/pimeet pimeet
        fi

        # Create directories
        mkdir -p /var/lib/pimeet
        mkdir -p /var/log/pimeet
        mkdir -p /etc/pimeet

        # Set permissions
        chown -R pimeet:pimeet /var/lib/pimeet
        chown -R pimeet:pimeet /var/log/pimeet
        chown -R root:pimeet /etc/pimeet
        chmod 750 /etc/pimeet

"""
        if package_type == PackageType.CORE:
            script += """
        # Enable and start service
        systemctl daemon-reload
        systemctl enable pimeet.service
"""

        script += """
        ;;
esac

exit 0
"""
        postinst.write_text(script)
        postinst.chmod(0o755)

    async def _create_prerm(self, build_dir: Path, package_type: PackageType) -> None:
        """Create pre-removal script."""
        prerm = build_dir / "DEBIAN/prerm"

        script = """#!/bin/bash
set -e

case "$1" in
    remove|upgrade|deconfigure)
"""
        if package_type == PackageType.CORE:
            script += """
        # Stop service
        systemctl stop pimeet.service || true
        systemctl disable pimeet.service || true
"""

        script += """
        ;;
esac

exit 0
"""
        prerm.write_text(script)
        prerm.chmod(0o755)

    async def _build_deb(self, build_dir: Path, pkg_info: PackageInfo) -> Optional[Path]:
        """Build .deb file using dpkg-deb."""
        deb_name = f"{pkg_info.name}_{pkg_info.version}_{pkg_info.architecture.value}.deb"
        deb_path = build_dir.parent / deb_name

        try:
            result = subprocess.run(
                ["dpkg-deb", "--build", str(build_dir), str(deb_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return deb_path
            else:
                logger.error(f"dpkg-deb failed: {result.stderr}")
                return None

        except FileNotFoundError:
            logger.error("dpkg-deb not found")
            return None

    async def _sign_package(self, deb_path: Path) -> bool:
        """Sign package with GPG key."""
        try:
            result = subprocess.run(
                ["dpkg-sig", "-k", self._gpg_key, "--sign", "builder", str(deb_path)],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            logger.warning("dpkg-sig not found, package not signed")
            return False


class APTRepository:
    """
    APT repository management for PiMeet packages.
    """

    def __init__(
        self,
        repo_dir: str,
        gpg_key: Optional[str] = None,
        origin: str = "PiMeet",
        label: str = "PiMeet Repository",
    ):
        self._repo_dir = Path(repo_dir)
        self._gpg_key = gpg_key
        self._origin = origin
        self._label = label

        self._repo_dir.mkdir(parents=True, exist_ok=True)

    async def add_package(
        self,
        deb_path: str,
        distribution: Distribution,
        component: str = "main",
    ) -> bool:
        """Add a package to the repository."""
        deb_file = Path(deb_path)
        if not deb_file.exists():
            logger.error(f"Package not found: {deb_path}")
            return False

        # Create pool directory
        pool_dir = self._repo_dir / "pool" / component
        pool_dir.mkdir(parents=True, exist_ok=True)

        # Copy package to pool
        dest = pool_dir / deb_file.name
        shutil.copy(deb_file, dest)

        # Update repository metadata
        await self._update_metadata(distribution, component)

        logger.info(f"Added package to repository: {deb_file.name}")
        return True

    async def _update_metadata(
        self,
        distribution: Distribution,
        component: str,
    ) -> None:
        """Update repository metadata (Packages, Release files)."""
        dist_dir = self._repo_dir / "dists" / distribution.value
        comp_dir = dist_dir / component

        # Generate Packages file for each architecture
        for arch in [Architecture.ARM64, Architecture.ARMHF, Architecture.ALL]:
            arch_dir = comp_dir / f"binary-{arch.value}"
            arch_dir.mkdir(parents=True, exist_ok=True)

            packages_content = await self._generate_packages(component, arch)
            packages_file = arch_dir / "Packages"
            packages_file.write_text(packages_content)

            # Compress
            await self._compress_file(packages_file)

        # Generate Release file
        await self._generate_release(dist_dir, distribution, [component])

    async def _generate_packages(
        self,
        component: str,
        architecture: Architecture,
    ) -> str:
        """Generate Packages index file."""
        pool_dir = self._repo_dir / "pool" / component
        packages = []

        if not pool_dir.exists():
            return ""

        for deb_file in pool_dir.glob("*.deb"):
            # Get package info
            pkg_info = await self._get_package_info(deb_file)
            if pkg_info:
                # Check architecture
                pkg_arch = pkg_info.get("Architecture", "all")
                if pkg_arch == architecture.value or pkg_arch == "all":
                    pkg_info["Filename"] = f"pool/{component}/{deb_file.name}"
                    pkg_info["Size"] = str(deb_file.stat().st_size)

                    # Calculate checksums
                    with open(deb_file, "rb") as f:
                        content = f.read()
                        pkg_info["MD5sum"] = hashlib.md5(content).hexdigest()
                        pkg_info["SHA256"] = hashlib.sha256(content).hexdigest()

                    packages.append(pkg_info)

        # Format output
        output = []
        for pkg in packages:
            for key, value in pkg.items():
                if key == "Description" and "\n" in value:
                    output.append(f"{key}: {value.split(chr(10))[0]}")
                    for line in value.split("\n")[1:]:
                        output.append(f" {line}")
                else:
                    output.append(f"{key}: {value}")
            output.append("")

        return "\n".join(output)

    async def _get_package_info(self, deb_path: Path) -> Optional[Dict[str, str]]:
        """Extract package information from .deb file."""
        try:
            result = subprocess.run(
                ["dpkg-deb", "-I", str(deb_path), "control"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return None

            info = {}
            current_key = None

            for line in result.stdout.split("\n"):
                if line.startswith(" ") and current_key:
                    info[current_key] += "\n" + line.strip()
                elif ": " in line:
                    key, value = line.split(": ", 1)
                    info[key] = value
                    current_key = key

            return info

        except Exception as e:
            logger.error(f"Failed to get package info: {e}")
            return None

    async def _generate_release(
        self,
        dist_dir: Path,
        distribution: Distribution,
        components: List[str],
    ) -> None:
        """Generate Release file."""
        release_content = [
            f"Origin: {self._origin}",
            f"Label: {self._label}",
            f"Suite: {distribution.value}",
            f"Codename: {distribution.value}",
            f"Architectures: arm64 armhf all",
            f"Components: {' '.join(components)}",
            f"Date: {datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S UTC')}",
        ]

        # Add checksums for index files
        checksums_md5 = ["MD5Sum:"]
        checksums_sha256 = ["SHA256:"]

        for component in components:
            comp_dir = dist_dir / component

            for arch in ["arm64", "armhf", "all"]:
                for filename in ["Packages", "Packages.gz"]:
                    file_path = comp_dir / f"binary-{arch}" / filename
                    if file_path.exists():
                        with open(file_path, "rb") as f:
                            content = f.read()

                        relative_path = f"{component}/binary-{arch}/{filename}"
                        size = len(content)
                        md5 = hashlib.md5(content).hexdigest()
                        sha256 = hashlib.sha256(content).hexdigest()

                        checksums_md5.append(f" {md5} {size:>8} {relative_path}")
                        checksums_sha256.append(f" {sha256} {size:>8} {relative_path}")

        release_content.extend(checksums_md5)
        release_content.extend(checksums_sha256)

        release_file = dist_dir / "Release"
        release_file.write_text("\n".join(release_content))

        # Sign Release file
        if self._gpg_key:
            await self._sign_release(release_file)

    async def _sign_release(self, release_file: Path) -> None:
        """Sign Release file with GPG."""
        try:
            # Create InRelease (clearsigned)
            subprocess.run([
                "gpg", "--default-key", self._gpg_key,
                "--clearsign", "-o", str(release_file.parent / "InRelease"),
                str(release_file),
            ], check=True)

            # Create Release.gpg (detached signature)
            subprocess.run([
                "gpg", "--default-key", self._gpg_key,
                "-abs", "-o", str(release_file.parent / "Release.gpg"),
                str(release_file),
            ], check=True)

        except Exception as e:
            logger.error(f"Failed to sign Release: {e}")

    async def _compress_file(self, file_path: Path) -> None:
        """Compress file with gzip."""
        import gzip

        with open(file_path, "rb") as f_in:
            with gzip.open(f"{file_path}.gz", "wb") as f_out:
                f_out.write(f_in.read())


class APTUpdateService:
    """
    APT-based update service for PiMeet.
    """

    def __init__(
        self,
        repo_url: str = "https://apt.pimeet.io",
        distribution: Distribution = Distribution.BOOKWORM,
    ):
        self._repo_url = repo_url
        self._distribution = distribution

    async def configure_repository(self) -> bool:
        """Configure APT repository on the system."""
        try:
            # Add repository source
            source_content = f"""deb {self._repo_url} {self._distribution.value} main
"""
            source_file = Path("/etc/apt/sources.list.d/pimeet.list")
            source_file.write_text(source_content)

            # Download and add GPG key
            key_url = f"{self._repo_url}/gpg-key.pub"

            # Import key
            subprocess.run([
                "curl", "-fsSL", key_url, "|",
                "gpg", "--dearmor", "-o", "/usr/share/keyrings/pimeet-archive-keyring.gpg",
            ], shell=True, check=True)

            # Update sources to use keyring
            source_content = f"""deb [signed-by=/usr/share/keyrings/pimeet-archive-keyring.gpg] {self._repo_url} {self._distribution.value} main
"""
            source_file.write_text(source_content)

            logger.info("APT repository configured")
            return True

        except Exception as e:
            logger.error(f"Failed to configure repository: {e}")
            return False

    async def check_updates(self) -> Dict[str, Any]:
        """Check for available updates."""
        try:
            # Update package lists
            subprocess.run(["apt", "update"], capture_output=True, check=True)

            # Check for upgradable pimeet packages
            result = subprocess.run(
                ["apt", "list", "--upgradable"],
                capture_output=True,
                text=True,
            )

            updates = []
            for line in result.stdout.split("\n"):
                if "pimeet" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        updates.append({
                            "package": parts[0].split("/")[0],
                            "version": parts[1],
                        })

            return {
                "available": len(updates) > 0,
                "updates": updates,
            }

        except Exception as e:
            logger.error(f"Failed to check updates: {e}")
            return {"available": False, "updates": [], "error": str(e)}

    async def install_updates(self, packages: List[str] = None) -> bool:
        """Install available updates."""
        try:
            if packages:
                cmd = ["apt", "install", "-y"] + packages
            else:
                cmd = ["apt", "upgrade", "-y", "pimeet*"]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Updates installed successfully")
                return True
            else:
                logger.error(f"Update failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to install updates: {e}")
            return False

    async def get_installed_version(self, package: str = "pimeet") -> Optional[str]:
        """Get installed package version."""
        try:
            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Version}", package],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return result.stdout.strip()
            return None

        except Exception:
            return None
