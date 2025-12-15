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
    NUC = "nuc"  # Intel NUC or mini PCs
    SERVER = "server"  # Server/workstation class
    JETSON = "jetson"  # NVIDIA Jetson
    UNKNOWN = "unknown"


class GPUVendor(Enum):
    """GPU vendors for AI acceleration."""
    NVIDIA = "nvidia"
    INTEL = "intel"
    AMD = "amd"
    NONE = "none"


class Architecture(Enum):
    """CPU architectures."""
    ARM64 = "aarch64"
    AMD64 = "x86_64"
    ARM32 = "armv7l"
    UNKNOWN = "unknown"


@dataclass
class GPUInfo:
    """GPU information."""
    vendor: GPUVendor = GPUVendor.NONE
    name: str = ""
    driver_version: str = ""
    memory_mb: int = 0
    cuda_cores: int = 0  # NVIDIA
    compute_units: int = 0  # AMD/Intel
    supports_cuda: bool = False
    supports_opencl: bool = False
    supports_openvino: bool = False
    supports_rocm: bool = False


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
    # x86_64 specific
    gpu: Optional[GPUInfo] = None
    has_ddc_ci: bool = False  # DDC/CI monitor control
    has_usb_camera: bool = False
    cpu_vendor: str = ""  # intel, amd
    has_avx2: bool = False  # Advanced Vector Extensions
    has_avx512: bool = False

    @property
    def is_raspberry_pi(self) -> bool:
        return self.device in (
            DeviceType.RASPBERRY_PI_5,
            DeviceType.RASPBERRY_PI_4,
            DeviceType.RASPBERRY_PI_3,
        )

    @property
    def is_x86_64(self) -> bool:
        return self.arch == Architecture.AMD64

    @property
    def is_64bit(self) -> bool:
        return self.arch in (Architecture.ARM64, Architecture.AMD64)

    @property
    def is_desktop_class(self) -> bool:
        """Check if this is a desktop/server class machine."""
        return self.device in (DeviceType.PC, DeviceType.NUC, DeviceType.SERVER)

    @property
    def supports_hailo(self) -> bool:
        """Hailo AI Kit only works on Pi 5."""
        return self.device == DeviceType.RASPBERRY_PI_5

    @property
    def supports_coral(self) -> bool:
        """Coral USB works on any platform with USB 3.0."""
        return self.is_64bit

    @property
    def supports_nvidia_gpu(self) -> bool:
        """Check if NVIDIA GPU acceleration is available."""
        return self.gpu is not None and self.gpu.vendor == GPUVendor.NVIDIA

    @property
    def supports_intel_gpu(self) -> bool:
        """Check if Intel GPU (Arc/Xe) acceleration is available."""
        return self.gpu is not None and self.gpu.vendor == GPUVendor.INTEL

    @property
    def supports_amd_gpu(self) -> bool:
        """Check if AMD GPU (ROCm) acceleration is available."""
        return self.gpu is not None and self.gpu.vendor == GPUVendor.AMD

    @property
    def best_ai_accelerator(self) -> str:
        """Return the best available AI accelerator."""
        if "hailo" in self.ai_accelerators:
            return "hailo"
        if "nvidia" in self.ai_accelerators:
            return "nvidia"
        if "coral" in self.ai_accelerators:
            return "coral"
        if "intel" in self.ai_accelerators:
            return "intel"
        if "amd" in self.ai_accelerators:
            return "amd"
        return "cpu"


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
        info.cpu_vendor = cls._detect_cpu_vendor()

        # Detect memory
        info.memory_total_mb = cls._detect_memory()

        # x86_64 specific detection
        if info.arch == Architecture.AMD64:
            info.gpu = cls._detect_gpu()
            info.has_avx2 = cls._detect_avx2()
            info.has_avx512 = cls._detect_avx512()
            info.has_ddc_ci = cls._detect_ddc_ci()
            info.has_usb_camera = cls._detect_usb_camera()

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
        """Detect device type (Pi, PC, NUC, Server, Jetson, etc.)."""
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
                elif "Jetson" in model or "NVIDIA" in model:
                    return DeviceType.JETSON
            except Exception:
                pass

        # Check for x86_64 architecture (PC/NUC/Server)
        if platform.machine() in ("x86_64", "amd64"):
            # Detect specific x86_64 device types
            return PlatformDetector._detect_x86_device_type()

        return DeviceType.UNKNOWN

    @staticmethod
    def _detect_x86_device_type() -> DeviceType:
        """Detect specific x86_64 device type."""
        # Check DMI information for device identification
        dmi_paths = {
            "product_name": "/sys/class/dmi/id/product_name",
            "board_vendor": "/sys/class/dmi/id/board_vendor",
            "sys_vendor": "/sys/class/dmi/id/sys_vendor",
            "chassis_type": "/sys/class/dmi/id/chassis_type",
        }

        dmi_info = {}
        for key, path in dmi_paths.items():
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        dmi_info[key] = f.read().strip().lower()
                except Exception:
                    pass

        product = dmi_info.get("product_name", "")
        vendor = dmi_info.get("sys_vendor", "") or dmi_info.get("board_vendor", "")
        chassis = dmi_info.get("chassis_type", "")

        # Intel NUC detection
        if "nuc" in product or "nuc" in vendor:
            return DeviceType.NUC

        # Other mini PCs (Beelink, Minisforum, etc.)
        mini_pc_keywords = ["beelink", "minisforum", "acepc", "chuwi", "gmk", "trigkey"]
        if any(kw in product or kw in vendor for kw in mini_pc_keywords):
            return DeviceType.NUC

        # Server detection (based on chassis type)
        # Chassis type 17=Rack Mount, 23=Rack Mount Chassis
        server_chassis_types = ["17", "23", "7", "25"]  # 7=Tower server, 25=Multi-system chassis
        if chassis in server_chassis_types:
            return DeviceType.SERVER

        # Server vendor detection
        server_vendors = ["dell", "hp", "hpe", "lenovo", "supermicro", "gigabyte"]
        server_keywords = ["server", "proliant", "poweredge", "thinksystem"]
        if any(sv in vendor for sv in server_vendors):
            if any(sk in product for sk in server_keywords):
                return DeviceType.SERVER

        # VM/Cloud detection (treat as server)
        vm_vendors = ["qemu", "vmware", "virtualbox", "kvm", "xen", "microsoft corporation"]
        if any(vm in vendor for vm in vm_vendors):
            return DeviceType.SERVER

        return DeviceType.PC

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
    def _detect_cpu_vendor() -> str:
        """Detect CPU vendor (Intel, AMD, ARM)."""
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("vendor_id"):
                        vendor = line.split(":")[1].strip().lower()
                        if "intel" in vendor or "genuineintel" in vendor:
                            return "intel"
                        elif "amd" in vendor or "authenticamd" in vendor:
                            return "amd"
                    elif line.startswith("CPU implementer"):
                        # ARM CPUs
                        return "arm"
        except Exception:
            pass
        return "unknown"

    @staticmethod
    def _detect_gpu() -> Optional[GPUInfo]:
        """Detect GPU information for x86_64 systems."""
        gpu_info = None

        # Try NVIDIA first
        gpu_info = PlatformDetector._detect_nvidia_gpu()
        if gpu_info:
            return gpu_info

        # Try Intel GPU
        gpu_info = PlatformDetector._detect_intel_gpu()
        if gpu_info:
            return gpu_info

        # Try AMD GPU
        gpu_info = PlatformDetector._detect_amd_gpu()
        if gpu_info:
            return gpu_info

        return None

    @staticmethod
    def _detect_nvidia_gpu() -> Optional[GPUInfo]:
        """Detect NVIDIA GPU."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(", ")
                if len(parts) >= 3:
                    return GPUInfo(
                        vendor=GPUVendor.NVIDIA,
                        name=parts[0].strip(),
                        driver_version=parts[1].strip(),
                        memory_mb=int(float(parts[2].strip())),
                        supports_cuda=True,
                        supports_opencl=True,
                    )
        except Exception:
            pass
        return None

    @staticmethod
    def _detect_intel_gpu() -> Optional[GPUInfo]:
        """Detect Intel integrated/discrete GPU (Arc, Xe, UHD)."""
        try:
            # Check for Intel GPU via lspci
            result = subprocess.run(
                ["lspci", "-v"],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout.lower()
                if "intel" in output and ("vga" in output or "display" in output):
                    # Extract GPU name
                    for line in result.stdout.split("\n"):
                        if "VGA" in line and "Intel" in line:
                            name = line.split(":")[-1].strip()

                            # Check for Arc/Xe (discrete)
                            is_arc = "arc" in name.lower()

                            # Check if OpenVINO is available
                            has_openvino = PlatformDetector._check_openvino()

                            return GPUInfo(
                                vendor=GPUVendor.INTEL,
                                name=name,
                                supports_opencl=True,
                                supports_openvino=has_openvino,
                                compute_units=96 if is_arc else 32,  # Approximate
                            )
        except Exception:
            pass
        return None

    @staticmethod
    def _detect_amd_gpu() -> Optional[GPUInfo]:
        """Detect AMD GPU (RDNA, CDNA)."""
        try:
            # Check for AMD GPU via lspci
            result = subprocess.run(
                ["lspci", "-v"],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout.lower()
                if "amd" in output and ("vga" in output or "display" in output):
                    # Extract GPU name
                    for line in result.stdout.split("\n"):
                        if "VGA" in line and ("AMD" in line or "ATI" in line):
                            name = line.split(":")[-1].strip()

                            # Check for ROCm
                            has_rocm = PlatformDetector._check_rocm()

                            return GPUInfo(
                                vendor=GPUVendor.AMD,
                                name=name,
                                supports_opencl=True,
                                supports_rocm=has_rocm,
                            )
        except Exception:
            pass
        return None

    @staticmethod
    def _check_openvino() -> bool:
        """Check if OpenVINO is available."""
        try:
            result = subprocess.run(
                ["python3", "-c", "import openvino"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _check_rocm() -> bool:
        """Check if ROCm is available."""
        try:
            result = subprocess.run(
                ["rocm-smi", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _detect_avx2() -> bool:
        """Check if CPU supports AVX2."""
        try:
            with open("/proc/cpuinfo") as f:
                content = f.read()
                return "avx2" in content.lower()
        except Exception:
            return False

    @staticmethod
    def _detect_avx512() -> bool:
        """Check if CPU supports AVX-512."""
        try:
            with open("/proc/cpuinfo") as f:
                content = f.read()
                return "avx512" in content.lower()
        except Exception:
            return False

    @staticmethod
    def _detect_ddc_ci() -> bool:
        """Check if DDC/CI monitor control is available."""
        try:
            result = subprocess.run(
                ["which", "ddcutil"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                # Try to detect monitors
                detect_result = subprocess.run(
                    ["ddcutil", "detect", "--brief"],
                    capture_output=True,
                    timeout=10
                )
                return detect_result.returncode == 0 and b"Display" in detect_result.stdout
        except Exception:
            pass
        return False

    @staticmethod
    def _detect_usb_camera() -> bool:
        """Detect USB webcam."""
        try:
            result = subprocess.run(
                ["v4l2-ctl", "--list-devices"],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout.lower()
                # Look for USB camera identifiers
                usb_indicators = ["usb", "webcam", "logitech", "microsoft", "hd pro", "c920", "c930"]
                return any(ind in output for ind in usb_indicators)
        except Exception:
            pass

        # Fallback: check for video devices
        return os.path.exists("/dev/video0")

    @staticmethod
    def _detect_ai_accelerators(info: PlatformInfo) -> List[str]:
        """Detect available AI accelerators."""
        accelerators = []

        # Check for Hailo (Pi 5 only, via PCIe)
        if info.device == DeviceType.RASPBERRY_PI_5:
            try:
                result = subprocess.run(
                    ["hailortcli", "fw-control", "identify"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    accelerators.append("hailo")
            except Exception:
                pass

        # Check for NVIDIA Jetson
        if info.device == DeviceType.JETSON:
            accelerators.append("nvidia")

        # Check for Coral EdgeTPU (USB) - works on all platforms
        try:
            if os.path.exists("/dev/bus/usb"):
                result = subprocess.run(
                    ["lsusb", "-d", "1a6e:089a"],  # Coral USB Accelerator
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout:
                    if "coral" not in accelerators:
                        accelerators.append("coral")

                # Also check for Coral M.2
                result = subprocess.run(
                    ["lsusb", "-d", "18d1:9302"],  # Coral M.2
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout:
                    if "coral" not in accelerators:
                        accelerators.append("coral")
        except Exception:
            pass

        # x86_64 GPU-based accelerators
        if info.arch == Architecture.AMD64 and info.gpu:
            if info.gpu.vendor == GPUVendor.NVIDIA:
                if "nvidia" not in accelerators:
                    accelerators.append("nvidia")
            elif info.gpu.vendor == GPUVendor.INTEL:
                accelerators.append("intel")
            elif info.gpu.vendor == GPUVendor.AMD:
                accelerators.append("amd")

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
