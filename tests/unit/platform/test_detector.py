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
    PlatformInfo,
)


class TestArchitecture:
    """Tests for Architecture enum."""

    def test_values(self):
        """Test architecture enum values."""
        assert Architecture.ARM64.value == "aarch64"
        assert Architecture.ARM32.value == "armv7l"
        assert Architecture.AMD64.value == "x86_64"
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


class TestPlatformInfo:
    """Tests for PlatformInfo dataclass."""

    def test_default_values(self):
        """Test default platform info values."""
        info = PlatformInfo()
        assert info.device == DeviceType.UNKNOWN
        assert info.arch == Architecture.UNKNOWN

    def test_is_raspberry_pi(self):
        """Test is_raspberry_pi property."""
        info = PlatformInfo(device=DeviceType.RASPBERRY_PI_5)
        assert info.is_raspberry_pi is True

        info = PlatformInfo(device=DeviceType.PC)
        assert info.is_raspberry_pi is False


class TestPlatformDetector:
    """Tests for PlatformDetector class."""

    def test_detect_returns_platform_info(self):
        """Test that detect() returns PlatformInfo."""
        # Clear cached info to force detection
        PlatformDetector._cached_info = None

        info = PlatformDetector.detect()
        assert isinstance(info, PlatformInfo)

    def test_detect_architecture_aarch64(self):
        """Test detection of aarch64 architecture."""
        with patch("platform.machine", return_value="aarch64"):
            arch = PlatformDetector._detect_architecture()
            assert arch == Architecture.ARM64

    def test_detect_architecture_x86_64(self):
        """Test detection of x86_64 architecture."""
        with patch("platform.machine", return_value="x86_64"):
            arch = PlatformDetector._detect_architecture()
            assert arch == Architecture.AMD64

    def test_detect_architecture_armv7l(self):
        """Test detection of armv7l architecture."""
        with patch("platform.machine", return_value="armv7l"):
            arch = PlatformDetector._detect_architecture()
            assert arch == Architecture.ARM32

    def test_detect_device_rpi5(self):
        """Test detection of Raspberry Pi 5."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=b"Raspberry Pi 5 Model B Rev 1.0")):
                device = PlatformDetector._detect_device()
                assert device == DeviceType.RASPBERRY_PI_5

    def test_detect_device_rpi4(self):
        """Test detection of Raspberry Pi 4."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=b"Raspberry Pi 4 Model B Rev 1.4")):
                device = PlatformDetector._detect_device()
                assert device == DeviceType.RASPBERRY_PI_4

    def test_detect_device_jetson(self):
        """Test detection of NVIDIA Jetson."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=b"NVIDIA Jetson Xavier NX")):
                device = PlatformDetector._detect_device()
                assert device == DeviceType.JETSON

    def test_detect_device_pc_no_model_file(self):
        """Test detection falls back to PC detection when no model file."""
        with patch("os.path.exists", return_value=False):
            with patch("platform.machine", return_value="x86_64"):
                with patch.object(PlatformDetector, "_detect_x86_device_type", return_value=DeviceType.PC):
                    device = PlatformDetector._detect_device()
                    assert device in [DeviceType.PC, DeviceType.NUC, DeviceType.SERVER, DeviceType.UNKNOWN]

    def test_detect_os(self):
        """Test OS detection."""
        os_release_content = '''ID=ubuntu
VERSION_ID="22.04"
VERSION_CODENAME=jammy
'''
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=os_release_content)):
                os_name, os_version, os_codename = PlatformDetector._detect_os()
                assert os_name == "ubuntu"
                assert os_version == "22.04"
                assert os_codename == "jammy"


class TestPlatformDetectorGPU:
    """Tests for GPU detection."""

    def test_detect_nvidia_gpu(self):
        """Test NVIDIA GPU detection."""
        nvidia_output = "NVIDIA GeForce RTX 3080, 535.129.03, 10240"
        with patch("shutil.which", return_value="/usr/bin/nvidia-smi"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=nvidia_output)
                gpu = PlatformDetector._detect_nvidia_gpu()
                assert gpu.vendor == GPUVendor.NVIDIA

    def test_no_nvidia_gpu(self):
        """Test when NVIDIA GPU not present."""
        with patch("shutil.which", return_value=None):
            gpu = PlatformDetector._detect_nvidia_gpu()
            # Returns None or GPUInfo with vendor NONE when no nvidia-smi
            assert gpu is None or gpu.vendor == GPUVendor.NONE


class TestPlatformDetectorFeatures:
    """Tests for feature detection."""

    def test_detect_gpio(self):
        """Test GPIO detection."""
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            result = PlatformDetector._detect_gpio()
            assert isinstance(result, bool)

    def test_detect_hdmi_cec(self):
        """Test HDMI CEC detection."""
        result = PlatformDetector._detect_hdmi_cec()
        assert isinstance(result, bool)

    def test_detect_camera_module(self):
        """Test camera module detection."""
        result = PlatformDetector._detect_camera_module()
        assert isinstance(result, bool)

    def test_detect_avx2(self):
        """Test AVX2 detection."""
        cpuinfo_content = "flags: fpu avx avx2 sse4_2"
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cpuinfo_content)):
                result = PlatformDetector._detect_avx2()
                assert result is True

    def test_detect_avx2_not_present(self):
        """Test AVX2 detection when not present."""
        cpuinfo_content = "flags: fpu sse4_2"
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cpuinfo_content)):
                result = PlatformDetector._detect_avx2()
                assert result is False


class TestPlatformDetectorCaching:
    """Tests for caching behavior."""

    def test_cache_is_used(self):
        """Test that cached info is returned on subsequent calls."""
        # Clear cache
        PlatformDetector._cached_info = None

        # First call should detect
        info1 = PlatformDetector.detect()

        # Second call should use cache
        info2 = PlatformDetector.detect()

        assert info1 is info2

    def test_force_refresh_bypasses_cache(self):
        """Test that force_refresh bypasses the cache."""
        # Clear cache and get initial info
        PlatformDetector._cached_info = None
        info1 = PlatformDetector.detect()

        # Force refresh should create new info
        info2 = PlatformDetector.detect(force_refresh=True)

        # They should be different objects (though content may be same)
        assert info1 is not info2
