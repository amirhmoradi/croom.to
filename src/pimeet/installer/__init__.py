"""
Installation system for PiMeet.

Provides modern installation, update, and configuration management
with support for multiple platforms and deployment scenarios.
"""

import asyncio
import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)


class InstallationType(Enum):
    """Installation types."""
    FULL = "full"  # Complete installation
    MINIMAL = "minimal"  # Core only
    UPDATE = "update"  # Update existing
    REPAIR = "repair"  # Repair installation


class PlatformType(Enum):
    """Supported platforms."""
    RASPBERRY_PI = "raspberry_pi"
    RASPBERRY_PI_5 = "raspberry_pi_5"
    GENERIC_LINUX = "generic_linux"
    UBUNTU = "ubuntu"
    DEBIAN = "debian"


class ComponentStatus(Enum):
    """Component installation status."""
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"
    FAILED = "failed"
    NEEDS_UPDATE = "needs_update"


@dataclass
class Component:
    """Installable component."""
    id: str
    name: str
    description: str
    version: str
    required: bool = False
    dependencies: List[str] = field(default_factory=list)
    size_mb: float = 0
    status: ComponentStatus = ComponentStatus.NOT_INSTALLED
    install_path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "required": self.required,
            "dependencies": self.dependencies,
            "size_mb": self.size_mb,
            "status": self.status.value,
        }


@dataclass
class InstallationConfig:
    """Installation configuration."""
    installation_type: InstallationType = InstallationType.FULL
    target_path: str = "/opt/pimeet"
    config_path: str = "/etc/pimeet"
    data_path: str = "/var/lib/pimeet"
    log_path: str = "/var/log/pimeet"
    components: List[str] = field(default_factory=list)
    create_service: bool = True
    enable_autostart: bool = True
    install_desktop_entry: bool = True


@dataclass
class InstallProgress:
    """Installation progress information."""
    total_steps: int
    current_step: int
    current_component: str
    message: str
    percent: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "current_component": self.current_component,
            "message": self.message,
            "percent": self.percent,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class PlatformDetector:
    """Detects the current platform and capabilities."""

    @staticmethod
    def detect() -> PlatformType:
        """Detect current platform."""
        # Check for Raspberry Pi
        if Path("/proc/device-tree/model").exists():
            try:
                model = Path("/proc/device-tree/model").read_text()
                if "Raspberry Pi 5" in model:
                    return PlatformType.RASPBERRY_PI_5
                elif "Raspberry Pi" in model:
                    return PlatformType.RASPBERRY_PI
            except Exception:
                pass

        # Check Linux distribution
        if Path("/etc/os-release").exists():
            try:
                content = Path("/etc/os-release").read_text()
                if "ubuntu" in content.lower():
                    return PlatformType.UBUNTU
                elif "debian" in content.lower():
                    return PlatformType.DEBIAN
            except Exception:
                pass

        return PlatformType.GENERIC_LINUX

    @staticmethod
    def get_platform_info() -> Dict[str, Any]:
        """Get detailed platform information."""
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }

        # Memory
        try:
            import psutil
            mem = psutil.virtual_memory()
            info["memory_total_gb"] = mem.total / (1024 ** 3)
            info["memory_available_gb"] = mem.available / (1024 ** 3)
        except ImportError:
            pass

        # Disk
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            info["disk_total_gb"] = total / (1024 ** 3)
            info["disk_free_gb"] = free / (1024 ** 3)
        except Exception:
            pass

        return info


class DependencyManager:
    """Manages system dependencies."""

    # Package mappings for different package managers
    APT_PACKAGES = {
        "python3": "python3",
        "pip": "python3-pip",
        "chromium": "chromium-browser",
        "pulseaudio": "pulseaudio",
        "v4l-utils": "v4l-utils",
        "qt6": "qt6-base-dev",
        "libcec": "libcec-dev",
        "ffmpeg": "ffmpeg",
        "nodejs": "nodejs",
        "npm": "npm",
    }

    def __init__(self):
        self._platform = PlatformDetector.detect()

    def check_dependency(self, name: str) -> bool:
        """Check if a dependency is installed."""
        if name in self.APT_PACKAGES:
            return self._check_apt_package(self.APT_PACKAGES[name])

        # Check as command
        return shutil.which(name) is not None

    def _check_apt_package(self, package: str) -> bool:
        """Check if apt package is installed."""
        try:
            result = subprocess.run(
                ["dpkg", "-s", package],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    async def install_dependency(self, name: str) -> bool:
        """Install a dependency."""
        if name not in self.APT_PACKAGES:
            logger.warning(f"Unknown dependency: {name}")
            return False

        package = self.APT_PACKAGES[name]
        logger.info(f"Installing dependency: {package}")

        try:
            proc = await asyncio.create_subprocess_exec(
                "apt-get", "install", "-y", package,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"Failed to install {package}: {stderr.decode()}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error installing {package}: {e}")
            return False

    def get_missing_dependencies(self, required: List[str]) -> List[str]:
        """Get list of missing dependencies."""
        return [dep for dep in required if not self.check_dependency(dep)]


class Installer:
    """Main installation orchestrator."""

    VERSION = "1.0.0"

    COMPONENTS = [
        Component(
            id="core",
            name="PiMeet Core",
            description="Core service and platform support",
            version=VERSION,
            required=True,
            size_mb=50,
        ),
        Component(
            id="ui",
            name="Touch UI",
            description="Qt6/QML touch screen interface",
            version=VERSION,
            required=False,
            dependencies=["core"],
            size_mb=100,
        ),
        Component(
            id="dashboard",
            name="Dashboard Backend",
            description="Node.js dashboard backend",
            version=VERSION,
            required=False,
            dependencies=["core"],
            size_mb=80,
        ),
        Component(
            id="dashboard-frontend",
            name="Dashboard Frontend",
            description="React dashboard web interface",
            version=VERSION,
            required=False,
            dependencies=["dashboard"],
            size_mb=50,
        ),
        Component(
            id="ai",
            name="AI Features",
            description="AI-powered features (auto-framing, speaker tracking)",
            version=VERSION,
            required=False,
            dependencies=["core"],
            size_mb=200,
        ),
        Component(
            id="meeting-providers",
            name="Meeting Providers",
            description="Google Meet, Teams, Zoom support",
            version=VERSION,
            required=False,
            dependencies=["core"],
            size_mb=30,
        ),
    ]

    def __init__(
        self,
        config: Optional[InstallationConfig] = None,
        on_progress: Optional[Callable[[InstallProgress], None]] = None,
    ):
        self._config = config or InstallationConfig()
        self._on_progress = on_progress
        self._progress = InstallProgress(
            total_steps=0,
            current_step=0,
            current_component="",
            message="",
            percent=0,
        )

        self._platform = PlatformDetector.detect()
        self._deps = DependencyManager()
        self._components = {c.id: c for c in self.COMPONENTS}

    def _update_progress(
        self,
        step: int = None,
        component: str = None,
        message: str = None,
    ) -> None:
        """Update and emit progress."""
        if step is not None:
            self._progress.current_step = step
        if component is not None:
            self._progress.current_component = component
        if message is not None:
            self._progress.message = message

        self._progress.percent = (
            self._progress.current_step / self._progress.total_steps * 100
            if self._progress.total_steps > 0 else 0
        )

        if self._on_progress:
            self._on_progress(self._progress)

    async def install(self) -> bool:
        """Perform installation."""
        logger.info(f"Starting PiMeet installation v{self.VERSION}")
        logger.info(f"Platform: {self._platform.value}")
        logger.info(f"Installation type: {self._config.installation_type.value}")

        # Calculate total steps
        steps = [
            "Check prerequisites",
            "Install dependencies",
            "Create directories",
        ]

        components_to_install = self._get_components_to_install()
        for comp in components_to_install:
            steps.append(f"Install {comp.name}")

        steps.extend([
            "Create configuration",
            "Setup services",
            "Finalize installation",
        ])

        self._progress.total_steps = len(steps)
        current_step = 0

        try:
            # Step 1: Check prerequisites
            current_step += 1
            self._update_progress(current_step, "system", "Checking prerequisites...")
            if not await self._check_prerequisites():
                return False

            # Step 2: Install dependencies
            current_step += 1
            self._update_progress(current_step, "dependencies", "Installing dependencies...")
            if not await self._install_dependencies():
                return False

            # Step 3: Create directories
            current_step += 1
            self._update_progress(current_step, "directories", "Creating directories...")
            self._create_directories()

            # Install components
            for comp in components_to_install:
                current_step += 1
                self._update_progress(current_step, comp.id, f"Installing {comp.name}...")
                if not await self._install_component(comp):
                    comp.status = ComponentStatus.FAILED
                    self._progress.errors.append(f"Failed to install {comp.name}")
                else:
                    comp.status = ComponentStatus.INSTALLED

            # Create configuration
            current_step += 1
            self._update_progress(current_step, "config", "Creating configuration...")
            self._create_default_config()

            # Setup services
            current_step += 1
            self._update_progress(current_step, "services", "Setting up services...")
            if self._config.create_service:
                await self._setup_services()

            # Finalize
            current_step += 1
            self._update_progress(current_step, "finalize", "Finalizing installation...")
            self._finalize_installation()

            logger.info("Installation completed successfully")
            return True

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            self._progress.errors.append(str(e))
            return False

    async def _check_prerequisites(self) -> bool:
        """Check installation prerequisites."""
        # Check root/sudo
        if os.geteuid() != 0:
            self._progress.errors.append("Installation requires root privileges")
            return False

        # Check disk space
        try:
            total, used, free = shutil.disk_usage("/")
            required_mb = sum(c.size_mb for c in self._get_components_to_install()) + 500
            if free < required_mb * 1024 * 1024:
                self._progress.errors.append(
                    f"Insufficient disk space. Need {required_mb}MB, have {free // (1024*1024)}MB"
                )
                return False
        except Exception as e:
            self._progress.warnings.append(f"Could not check disk space: {e}")

        # Check memory
        try:
            import psutil
            mem = psutil.virtual_memory()
            if mem.total < 1024 * 1024 * 1024:  # 1GB minimum
                self._progress.warnings.append("System has less than 1GB RAM")
        except ImportError:
            pass

        return True

    async def _install_dependencies(self) -> bool:
        """Install system dependencies."""
        required_deps = ["python3", "pip", "chromium", "pulseaudio", "v4l-utils"]

        missing = self._deps.get_missing_dependencies(required_deps)
        if not missing:
            return True

        logger.info(f"Installing missing dependencies: {missing}")

        # Update package list
        proc = await asyncio.create_subprocess_exec(
            "apt-get", "update",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        # Install each dependency
        for dep in missing:
            if not await self._deps.install_dependency(dep):
                self._progress.warnings.append(f"Failed to install {dep}")

        return True

    def _create_directories(self) -> None:
        """Create installation directories."""
        directories = [
            self._config.target_path,
            self._config.config_path,
            self._config.data_path,
            self._config.log_path,
            f"{self._config.data_path}/meetings",
            f"{self._config.data_path}/cache",
            f"{self._config.data_path}/keys",
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")

    def _get_components_to_install(self) -> List[Component]:
        """Get list of components to install."""
        if self._config.components:
            # Specific components requested
            selected = []
            for comp_id in self._config.components:
                if comp_id in self._components:
                    comp = self._components[comp_id]
                    # Add dependencies
                    for dep_id in comp.dependencies:
                        dep = self._components.get(dep_id)
                        if dep and dep not in selected:
                            selected.append(dep)
                    if comp not in selected:
                        selected.append(comp)
            return selected

        # Full installation
        if self._config.installation_type == InstallationType.FULL:
            return list(self._components.values())

        # Minimal installation
        return [c for c in self._components.values() if c.required]

    async def _install_component(self, component: Component) -> bool:
        """Install a single component."""
        logger.info(f"Installing component: {component.name}")
        component.status = ComponentStatus.INSTALLING

        try:
            if component.id == "core":
                return await self._install_core()
            elif component.id == "ui":
                return await self._install_ui()
            elif component.id == "dashboard":
                return await self._install_dashboard()
            elif component.id == "dashboard-frontend":
                return await self._install_dashboard_frontend()
            elif component.id == "ai":
                return await self._install_ai()
            elif component.id == "meeting-providers":
                return await self._install_meeting_providers()

            return True

        except Exception as e:
            logger.error(f"Failed to install {component.name}: {e}")
            return False

    async def _install_core(self) -> bool:
        """Install core component."""
        target = Path(self._config.target_path)

        # Copy Python modules
        src_path = Path(__file__).parent.parent
        dst_path = target / "lib" / "python" / "pimeet"
        shutil.copytree(src_path, dst_path, dirs_exist_ok=True)

        # Install Python dependencies
        requirements_file = src_path.parent / "requirements.txt"
        if requirements_file.exists():
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

        return True

    async def _install_ui(self) -> bool:
        """Install Touch UI component."""
        target = Path(self._config.target_path) / "ui"
        target.mkdir(parents=True, exist_ok=True)

        # Copy QML files
        src_ui = Path(__file__).parent.parent.parent / "pimeet-ui"
        if src_ui.exists():
            shutil.copytree(src_ui, target, dirs_exist_ok=True)

        return True

    async def _install_dashboard(self) -> bool:
        """Install dashboard backend."""
        target = Path(self._config.target_path) / "dashboard"
        target.mkdir(parents=True, exist_ok=True)

        # Copy dashboard files
        src_dashboard = Path(__file__).parent.parent.parent / "pimeet-dashboard"
        if src_dashboard.exists():
            shutil.copytree(src_dashboard, target, dirs_exist_ok=True)

            # Install npm dependencies
            proc = await asyncio.create_subprocess_exec(
                "npm", "install", "--production",
                cwd=str(target),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

        return True

    async def _install_dashboard_frontend(self) -> bool:
        """Install dashboard frontend."""
        target = Path(self._config.target_path) / "dashboard" / "frontend"
        target.mkdir(parents=True, exist_ok=True)

        # Build frontend
        src_frontend = Path(__file__).parent.parent.parent / "pimeet-dashboard-frontend"
        if src_frontend.exists():
            # Install dependencies and build
            proc = await asyncio.create_subprocess_exec(
                "npm", "install",
                cwd=str(src_frontend),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            proc = await asyncio.create_subprocess_exec(
                "npm", "run", "build",
                cwd=str(src_frontend),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            # Copy build output
            build_dir = src_frontend / "build"
            if build_dir.exists():
                shutil.copytree(build_dir, target, dirs_exist_ok=True)

        return True

    async def _install_ai(self) -> bool:
        """Install AI component."""
        # AI models and dependencies
        target = Path(self._config.target_path) / "models"
        target.mkdir(parents=True, exist_ok=True)

        # Install additional Python packages
        ai_packages = ["onnxruntime", "numpy", "opencv-python-headless"]
        for package in ai_packages:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", package,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

        return True

    async def _install_meeting_providers(self) -> bool:
        """Install meeting providers."""
        # Install Chromium extensions/dependencies
        return True

    def _create_default_config(self) -> None:
        """Create default configuration files."""
        config_path = Path(self._config.config_path)

        # Main config
        main_config = {
            "version": self.VERSION,
            "room": {
                "name": "Conference Room",
                "display_name": "Conference Room",
            },
            "meeting": {
                "platforms": ["google_meet", "teams", "zoom"],
                "camera_default_on": True,
                "mic_default_on": True,
            },
            "ai": {
                "enabled": True,
                "backend": "auto",
                "auto_framing": True,
                "speaker_tracking": True,
                "occupancy_counting": True,
                "privacy_mode": False,
            },
            "dashboard": {
                "enabled": True,
                "port": 3000,
            },
            "security": {
                "tls_enabled": True,
                "api_auth_required": True,
            },
            "paths": {
                "data": self._config.data_path,
                "logs": self._config.log_path,
            },
        }

        (config_path / "config.json").write_text(
            json.dumps(main_config, indent=2)
        )

        # Device config
        device_config = {
            "device_id": self._generate_device_id(),
            "platform": self._platform.value,
            "installed_at": datetime.utcnow().isoformat(),
            "version": self.VERSION,
        }

        (config_path / "device.json").write_text(
            json.dumps(device_config, indent=2)
        )

    def _generate_device_id(self) -> str:
        """Generate unique device ID."""
        # Use MAC address and hostname
        import socket
        import uuid

        mac = uuid.getnode()
        hostname = socket.gethostname()
        combined = f"{mac}-{hostname}"

        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    async def _setup_services(self) -> None:
        """Setup systemd services."""
        # PiMeet Agent service
        agent_service = f"""[Unit]
Description=PiMeet Agent Service
After=network.target

[Service]
Type=simple
User=pimeet
Group=pimeet
WorkingDirectory={self._config.target_path}
ExecStart={sys.executable} -m pimeet.core.agent
Restart=always
RestartSec=10
Environment=PYTHONPATH={self._config.target_path}/lib/python

[Install]
WantedBy=multi-user.target
"""

        # Dashboard service
        dashboard_service = f"""[Unit]
Description=PiMeet Dashboard Service
After=network.target pimeet-agent.service

[Service]
Type=simple
User=pimeet
Group=pimeet
WorkingDirectory={self._config.target_path}/dashboard
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=10
Environment=NODE_ENV=production
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
"""

        # Write service files
        services_path = Path("/etc/systemd/system")

        (services_path / "pimeet-agent.service").write_text(agent_service)
        (services_path / "pimeet-dashboard.service").write_text(dashboard_service)

        # Create pimeet user if not exists
        try:
            subprocess.run(
                ["useradd", "-r", "-s", "/bin/false", "pimeet"],
                capture_output=True,
            )
        except Exception:
            pass

        # Set ownership
        subprocess.run(
            ["chown", "-R", "pimeet:pimeet", self._config.target_path],
            capture_output=True,
        )
        subprocess.run(
            ["chown", "-R", "pimeet:pimeet", self._config.data_path],
            capture_output=True,
        )

        # Reload systemd
        subprocess.run(["systemctl", "daemon-reload"], capture_output=True)

        # Enable services
        if self._config.enable_autostart:
            subprocess.run(
                ["systemctl", "enable", "pimeet-agent"],
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "enable", "pimeet-dashboard"],
                capture_output=True,
            )

    def _finalize_installation(self) -> None:
        """Finalize installation."""
        # Create version file
        version_file = Path(self._config.config_path) / "version"
        version_file.write_text(self.VERSION)

        # Create desktop entry if requested
        if self._config.install_desktop_entry:
            desktop_entry = f"""[Desktop Entry]
Name=PiMeet
Comment=Conference Room Management System
Exec={sys.executable} -m pimeet.ui.main
Icon={self._config.target_path}/assets/icon.png
Terminal=false
Type=Application
Categories=Office;Network;
"""
            desktop_path = Path("/usr/share/applications/pimeet.desktop")
            desktop_path.write_text(desktop_entry)

        logger.info("Installation finalized")

    @staticmethod
    def get_installed_version() -> Optional[str]:
        """Get currently installed version."""
        version_file = Path("/etc/pimeet/version")
        if version_file.exists():
            return version_file.read_text().strip()
        return None


class Uninstaller:
    """Handles PiMeet uninstallation."""

    def __init__(self, keep_config: bool = False, keep_data: bool = False):
        self._keep_config = keep_config
        self._keep_data = keep_data

    async def uninstall(self) -> bool:
        """Perform uninstallation."""
        logger.info("Starting PiMeet uninstallation")

        try:
            # Stop services
            subprocess.run(
                ["systemctl", "stop", "pimeet-agent"],
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "stop", "pimeet-dashboard"],
                capture_output=True,
            )

            # Disable services
            subprocess.run(
                ["systemctl", "disable", "pimeet-agent"],
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "disable", "pimeet-dashboard"],
                capture_output=True,
            )

            # Remove service files
            Path("/etc/systemd/system/pimeet-agent.service").unlink(missing_ok=True)
            Path("/etc/systemd/system/pimeet-dashboard.service").unlink(missing_ok=True)
            subprocess.run(["systemctl", "daemon-reload"], capture_output=True)

            # Remove installation
            shutil.rmtree("/opt/pimeet", ignore_errors=True)

            # Remove config if not keeping
            if not self._keep_config:
                shutil.rmtree("/etc/pimeet", ignore_errors=True)

            # Remove data if not keeping
            if not self._keep_data:
                shutil.rmtree("/var/lib/pimeet", ignore_errors=True)

            # Remove logs
            shutil.rmtree("/var/log/pimeet", ignore_errors=True)

            # Remove desktop entry
            Path("/usr/share/applications/pimeet.desktop").unlink(missing_ok=True)

            # Remove user
            subprocess.run(
                ["userdel", "pimeet"],
                capture_output=True,
            )

            logger.info("Uninstallation completed")
            return True

        except Exception as e:
            logger.error(f"Uninstallation failed: {e}")
            return False


async def install_pimeet(
    installation_type: InstallationType = InstallationType.FULL,
    on_progress: Optional[Callable[[InstallProgress], None]] = None,
) -> bool:
    """
    Main installation entry point.

    Args:
        installation_type: Type of installation
        on_progress: Progress callback

    Returns:
        True if installation succeeded
    """
    config = InstallationConfig(installation_type=installation_type)
    installer = Installer(config=config, on_progress=on_progress)
    return await installer.install()


from pimeet.installer.packaging import (
    PackageType,
    Architecture,
    Distribution,
    PackageInfo,
    DebianPackageBuilder,
    APTRepository,
    APTUpdateService,
    PACKAGE_DEFINITIONS,
)

from pimeet.installer.os_support import (
    OSType,
    OSRelease,
    OSInfo,
    VersionSnapshot,
    OSDetector,
    TrixieSupport,
    RollbackService,
    LegacyMigration,
)

__all__ = [
    # Core installation
    "InstallationType",
    "PlatformType",
    "ComponentStatus",
    "Component",
    "InstallationConfig",
    "InstallProgress",
    "PlatformDetector",
    "DependencyManager",
    "Installer",
    "Uninstaller",
    "install_pimeet",
    # Packaging
    "PackageType",
    "Architecture",
    "Distribution",
    "PackageInfo",
    "DebianPackageBuilder",
    "APTRepository",
    "APTUpdateService",
    "PACKAGE_DEFINITIONS",
    # OS Support
    "OSType",
    "OSRelease",
    "OSInfo",
    "VersionSnapshot",
    "OSDetector",
    "TrixieSupport",
    "RollbackService",
    "LegacyMigration",
]
