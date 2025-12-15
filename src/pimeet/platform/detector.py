"""
Platform detection module.

Detects the current hardware platform and available capabilities.
"""

import os
import platform
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class DeviceType(Enum):
    """Supported device types."""
    RASPBERRY_PI_5 = "rpi5"
    RASPBERRY_PI_4 = "rpi4"
    RASPBERRY_PI_3 = "rpi3"
    PC = "pc"
    UNKNOWN = "unknown"


class Architecture(Enum):
    """CPU architectures."""
    ARM64 = "aarch64"
    AMD64 = "x86_64"
    ARM32 = "armv7l"
    UNKNOWN = "unknown"


@dataclass
class PlatformInfo:
    """Information about the current platform."""
    device: DeviceType = DeviceType.UNKNOWN
    arch: Architecture = Architecture.UNKNOWN
    os_name: str = ""
    os_version: str = ""
    os_codename: str = ""
    kernel_version: str = ""
    cpu_model: str = ""
    cpu_cores: int = 0
    memory_total_mb: int = 0
    ai_accelerators: List[str] = field(default_factory=list)
    has_gpio: bool = False
    has_hdmi_cec: bool = False
    has_camera_module: bool = False
    has_touch_display: bool = False

    @property
    def is_raspberry_pi(self) -> bool:
        return self.device in (
            DeviceType.RASPBERRY_PI_5,
            DeviceType.RASPBERRY_PI_4,
            DeviceType.RASPBERRY_PI_3,
        )

    @property
    def is_64bit(self) -> bool:
        return self.arch in (Architecture.ARM64, Architecture.AMD64)

    @property
    def supports_hailo(self) -> bool:
        """Hailo AI Kit only works on Pi 5."""
        return self.device == DeviceType.RASPBERRY_PI_5

    @property
    def supports_coral(self) -> bool:
        """Coral USB works on any platform with USB 3.0."""
        return self.is_64bit


class PlatformDetector:
    """Detects and reports platform capabilities."""

    _cached_info: Optional[PlatformInfo] = None

    @classmethod
    def detect(cls, force_refresh: bool = False) -> PlatformInfo:
        """
        Detect the current platform.

        Args:
            force_refresh: If True, bypass cache and re-detect.

        Returns:
            PlatformInfo with detected capabilities.
        """
        if cls._cached_info is not None and not force_refresh:
            return cls._cached_info

        info = PlatformInfo()

        # Detect architecture
        info.arch = cls._detect_architecture()

        # Detect OS
        info.os_name, info.os_version, info.os_codename = cls._detect_os()
        info.kernel_version = platform.release()

        # Detect device type
        info.device = cls._detect_device()

        # Detect CPU
        info.cpu_model = cls._detect_cpu_model()
        info.cpu_cores = os.cpu_count() or 1

        # Detect memory
        info.memory_total_mb = cls._detect_memory()

        # Detect AI accelerators
        info.ai_accelerators = cls._detect_ai_accelerators(info)

        # Detect platform-specific features
        info.has_gpio = cls._detect_gpio()
        info.has_hdmi_cec = cls._detect_hdmi_cec()
        info.has_camera_module = cls._detect_camera_module()
        info.has_touch_display = cls._detect_touch_display()

        cls._cached_info = info
        return info

    @staticmethod
    def _detect_architecture() -> Architecture:
        """Detect CPU architecture."""
        machine = platform.machine().lower()
        if machine in ("aarch64", "arm64"):
            return Architecture.ARM64
        elif machine in ("x86_64", "amd64"):
            return Architecture.AMD64
        elif machine.startswith("armv7"):
            return Architecture.ARM32
        return Architecture.UNKNOWN

    @staticmethod
    def _detect_os() -> tuple:
        """Detect OS name, version, and codename."""
        os_name = "unknown"
        os_version = ""
        os_codename = ""

        # Try reading /etc/os-release
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("ID="):
                        os_name = line.split("=")[1].strip().strip('"')
                    elif line.startswith("VERSION_ID="):
                        os_version = line.split("=")[1].strip().strip('"')
                    elif line.startswith("VERSION_CODENAME="):
                        os_codename = line.split("=")[1].strip().strip('"')

        return os_name, os_version, os_codename

    @staticmethod
    def _detect_device() -> DeviceType:
        """Detect Raspberry Pi model or PC."""
        # Check for Raspberry Pi device tree
        model_path = "/proc/device-tree/model"
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    model = f.read().decode("utf-8", errors="ignore").strip("\x00")

                if "Raspberry Pi 5" in model:
                    return DeviceType.RASPBERRY_PI_5
                elif "Raspberry Pi 4" in model:
                    return DeviceType.RASPBERRY_PI_4
                elif "Raspberry Pi 3" in model:
                    return DeviceType.RASPBERRY_PI_3
            except Exception:
                pass

        # Check for x86_64 architecture (PC)
        if platform.machine() in ("x86_64", "amd64"):
            return DeviceType.PC

        return DeviceType.UNKNOWN

    @staticmethod
    def _detect_cpu_model() -> str:
        """Detect CPU model name."""
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name") or line.startswith("Model"):
                        return line.split(":")[1].strip()
        except Exception:
            pass
        return "Unknown"

    @staticmethod
    def _detect_memory() -> int:
        """Detect total memory in MB."""
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb // 1024
        except Exception:
            pass
        return 0

    @staticmethod
    def _detect_ai_accelerators(info: PlatformInfo) -> List[str]:
        """Detect available AI accelerators."""
        accelerators = []

        # Check for Hailo (Pi 5 only, via PCIe)
        if info.device == DeviceType.RASPBERRY_PI_5:
            try:
                # Check for Hailo device
                result = subprocess.run(
                    ["hailortcli", "fw-control", "identify"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    accelerators.append("hailo")
            except Exception:
                pass

        # Check for Coral EdgeTPU (USB)
        try:
            # Look for Coral USB device
            if os.path.exists("/dev/bus/usb"):
                result = subprocess.run(
                    ["lsusb", "-d", "1a6e:089a"],  # Coral USB Accelerator
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout:
                    accelerators.append("coral")

                # Also check for Coral M.2
                result = subprocess.run(
                    ["lsusb", "-d", "18d1:9302"],  # Coral M.2
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout:
                    accelerators.append("coral")
        except Exception:
            pass

        # Check for NVIDIA GPU (PC)
        if info.arch == Architecture.AMD64:
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout:
                    accelerators.append("nvidia")
            except Exception:
                pass

        # CPU is always available as fallback
        accelerators.append("cpu")

        return accelerators

    @staticmethod
    def _detect_gpio() -> bool:
        """Check if GPIO is available."""
        return os.path.exists("/sys/class/gpio") or os.path.exists("/dev/gpiochip0")

    @staticmethod
    def _detect_hdmi_cec() -> bool:
        """Check if HDMI-CEC is available."""
        try:
            result = subprocess.run(
                ["which", "cec-client"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _detect_camera_module() -> bool:
        """Check for Raspberry Pi camera module."""
        # Check for Pi camera
        if os.path.exists("/dev/video0"):
            try:
                result = subprocess.run(
                    ["v4l2-ctl", "--list-devices"],
                    capture_output=True,
                    timeout=5
                )
                output = result.stdout.decode()
                return "mmal" in output.lower() or "unicam" in output.lower()
            except Exception:
                pass
        return False

    @staticmethod
    def _detect_touch_display() -> bool:
        """Check for touch display."""
        # Check for touch input devices
        try:
            if os.path.exists("/dev/input"):
                for entry in os.listdir("/dev/input"):
                    if entry.startswith("event"):
                        # Check if it's a touch device
                        path = f"/sys/class/input/{entry}/device/name"
                        if os.path.exists(path):
                            with open(path) as f:
                                name = f.read().lower()
                                if "touch" in name or "ft5406" in name:
                                    return True
        except Exception:
            pass
        return False


def get_platform_info() -> PlatformInfo:
    """Convenience function to get platform info."""
    return PlatformDetector.detect()
