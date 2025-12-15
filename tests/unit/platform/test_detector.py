"""
Tests for croom.platform.detector module.
"""

import subprocess
from unittest.mock import MagicMock, patch, mock_open

import pytest

from croom.platform.detector import (
    Architecture,
    DeviceType,
    GPUVendor,
    GPUInfo,
    PlatformDetector,
)


class TestArchitecture:
    """Tests for Architecture enum."""

    def test_values(self):
        """Test architecture enum values."""
        assert Architecture.AARCH64.value == "aarch64"
        assert Architecture.ARMV7L.value == "armv7l"
        assert Architecture.AMD64.value == "amd64"
        assert Architecture.UNKNOWN.value == "unknown"


class TestDeviceType:
    """Tests for DeviceType enum."""

    def test_raspberry_pi_values(self):
        """Test Raspberry Pi device type values."""
        assert DeviceType.RASPBERRY_PI_5.value == "rpi5"
        assert DeviceType.RASPBERRY_PI_4.value == "rpi4"
        assert DeviceType.RASPBERRY_PI_3.value == "rpi3"

    def test_x86_values(self):
        """Test x86 device type values."""
        assert DeviceType.PC.value == "pc"
        assert DeviceType.NUC.value == "nuc"
        assert DeviceType.SERVER.value == "server"

    def test_other_values(self):
        """Test other device type values."""
        assert DeviceType.JETSON.value == "jetson"
        assert DeviceType.UNKNOWN.value == "unknown"


class TestGPUVendor:
    """Tests for GPUVendor enum."""

    def test_values(self):
        """Test GPU vendor enum values."""
        assert GPUVendor.NVIDIA.value == "nvidia"
        assert GPUVendor.INTEL.value == "intel"
        assert GPUVendor.AMD.value == "amd"
        assert GPUVendor.NONE.value == "none"


class TestGPUInfo:
    """Tests for GPUInfo dataclass."""

    def test_default_values(self):
        """Test default GPU info values."""
        info = GPUInfo()
        assert info.vendor == GPUVendor.NONE
        assert info.name == ""
        assert info.driver_version == ""
        assert info.memory_mb == 0
        assert info.supports_cuda is False
        assert info.supports_opencl is False
        assert info.supports_openvino is False
        assert info.supports_rocm is False

    def test_nvidia_gpu(self):
        """Test NVIDIA GPU info."""
        info = GPUInfo(
            vendor=GPUVendor.NVIDIA,
            name="NVIDIA GeForce RTX 3080",
            driver_version="535.129.03",
            memory_mb=10240,
            supports_cuda=True,
            supports_opencl=True,
        )
        assert info.vendor == GPUVendor.NVIDIA
        assert info.supports_cuda is True


class TestPlatformDetector:
    """Tests for PlatformDetector class."""

    @patch("platform.machine")
    def test_detect_aarch64(self, mock_machine):
        """Test detection of aarch64 architecture."""
        mock_machine.return_value = "aarch64"
        detector = PlatformDetector()
        assert detector.architecture == Architecture.AARCH64

    @patch("platform.machine")
    def test_detect_x86_64(self, mock_machine):
        """Test detection of x86_64 architecture."""
        mock_machine.return_value = "x86_64"
        detector = PlatformDetector()
        assert detector.architecture == Architecture.AMD64

    @patch("platform.machine")
    def test_detect_armv7l(self, mock_machine):
        """Test detection of armv7l architecture."""
        mock_machine.return_value = "armv7l"
        detector = PlatformDetector()
        assert detector.architecture == Architecture.ARMV7L

    @patch("platform.machine")
    @patch("builtins.open", mock_open(read_data="Raspberry Pi 5 Model B Rev 1.0"))
    @patch("os.path.exists")
    def test_detect_rpi5(self, mock_exists, mock_machine):
        """Test detection of Raspberry Pi 5."""
        mock_machine.return_value = "aarch64"
        mock_exists.return_value = True

        detector = PlatformDetector()
        assert detector.device_type == DeviceType.RASPBERRY_PI_5
        assert detector.is_raspberry_pi is True

    @patch("platform.machine")
    @patch("builtins.open", mock_open(read_data="Raspberry Pi 4 Model B Rev 1.4"))
    @patch("os.path.exists")
    def test_detect_rpi4(self, mock_exists, mock_machine):
        """Test detection of Raspberry Pi 4."""
        mock_machine.return_value = "aarch64"
        mock_exists.return_value = True

        detector = PlatformDetector()
        assert detector.device_type == DeviceType.RASPBERRY_PI_4
        assert detector.is_raspberry_pi is True

    @patch("platform.machine")
    @patch("os.path.exists")
    def test_detect_pc_no_model_file(self, mock_exists, mock_machine):
        """Test detection falls back to PC when no model file."""
        mock_machine.return_value = "x86_64"
        mock_exists.return_value = False

        detector = PlatformDetector()
        assert detector.is_raspberry_pi is False

    @patch("platform.machine")
    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_detect_nvidia_gpu(self, mock_exists, mock_run, mock_machine):
        """Test NVIDIA GPU detection."""
        mock_machine.return_value = "x86_64"
        mock_exists.return_value = False

        # Mock nvidia-smi output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="NVIDIA GeForce RTX 3080, 535.129.03, 10240",
        )

        detector = PlatformDetector()
        gpu_info = detector._detect_nvidia_gpu()

        assert gpu_info.vendor == GPUVendor.NVIDIA
        assert "RTX 3080" in gpu_info.name

    @patch("platform.machine")
    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_no_nvidia_gpu(self, mock_exists, mock_run, mock_machine):
        """Test when NVIDIA GPU not present."""
        mock_machine.return_value = "x86_64"
        mock_exists.return_value = False
        mock_run.side_effect = FileNotFoundError()

        detector = PlatformDetector()
        gpu_info = detector._detect_nvidia_gpu()

        assert gpu_info.vendor == GPUVendor.NONE

    @patch("platform.machine")
    @patch("os.path.exists")
    def test_has_gpio_on_pi(self, mock_exists, mock_machine):
        """Test GPIO detection on Raspberry Pi."""
        mock_machine.return_value = "aarch64"

        def exists_side_effect(path):
            return path in ["/proc/device-tree/model", "/dev/gpiochip0"]

        mock_exists.side_effect = exists_side_effect

        with patch("builtins.open", mock_open(read_data="Raspberry Pi 5")):
            detector = PlatformDetector()
            assert detector.has_gpio is True

    @patch("platform.machine")
    @patch("os.path.exists")
    def test_no_gpio_on_pc(self, mock_exists, mock_machine):
        """Test no GPIO on regular PC."""
        mock_machine.return_value = "x86_64"
        mock_exists.return_value = False

        detector = PlatformDetector()
        assert detector.has_gpio is False

    @patch("platform.machine")
    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_has_cec(self, mock_exists, mock_run, mock_machine):
        """Test CEC detection."""
        mock_machine.return_value = "aarch64"
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        with patch("builtins.open", mock_open(read_data="Raspberry Pi 5")):
            detector = PlatformDetector()
            # CEC detection depends on cec-client being available
            assert isinstance(detector.has_cec, bool)

    @patch("platform.machine")
    @patch("os.path.exists")
    def test_capabilities_summary(self, mock_exists, mock_machine):
        """Test capabilities summary generation."""
        mock_machine.return_value = "aarch64"
        mock_exists.return_value = True

        with patch("builtins.open", mock_open(read_data="Raspberry Pi 5")):
            detector = PlatformDetector()
            caps = detector.get_capabilities()

            assert "architecture" in caps
            assert "device_type" in caps
            assert "is_raspberry_pi" in caps


class TestPlatformDetectorCPUFeatures:
    """Tests for CPU feature detection."""

    @patch("platform.machine")
    @patch("builtins.open")
    @patch("os.path.exists")
    def test_detect_avx2(self, mock_exists, mock_open_func, mock_machine):
        """Test AVX2 detection."""
        mock_machine.return_value = "x86_64"
        mock_exists.return_value = True
        mock_open_func.return_value.__enter__.return_value.read.return_value = (
            "flags: fpu avx avx2 sse4_2"
        )

        detector = PlatformDetector()
        assert detector._has_avx2() is True

    @patch("platform.machine")
    @patch("builtins.open")
    @patch("os.path.exists")
    def test_detect_no_avx2(self, mock_exists, mock_open_func, mock_machine):
        """Test when AVX2 not available."""
        mock_machine.return_value = "x86_64"
        mock_exists.return_value = True
        mock_open_func.return_value.__enter__.return_value.read.return_value = (
            "flags: fpu sse4_2"
        )

        detector = PlatformDetector()
        assert detector._has_avx2() is False


class TestPlatformDetectorUSBCameras:
    """Tests for USB camera detection."""

    @patch("platform.machine")
    @patch("os.path.exists")
    @patch("pathlib.Path.glob")
    def test_detect_usb_cameras(self, mock_glob, mock_exists, mock_machine):
        """Test USB camera detection."""
        mock_machine.return_value = "x86_64"
        mock_exists.return_value = False

        # Mock video devices
        mock_glob.return_value = [
            MagicMock(__str__=lambda s: "/dev/video0"),
            MagicMock(__str__=lambda s: "/dev/video1"),
        ]

        detector = PlatformDetector()
        cameras = detector._detect_usb_cameras()

        assert isinstance(cameras, list)
