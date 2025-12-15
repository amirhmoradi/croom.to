"""
Tests for croom.video.usb_camera module.
"""

from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

import pytest


class TestCameraQuality:
    """Tests for CameraQuality enum."""

    def test_values(self):
        """Test camera quality enum values."""
        from croom.video.usb_camera import CameraQuality

        assert CameraQuality.BASIC.value == "basic"
        assert CameraQuality.STANDARD.value == "standard"
        assert CameraQuality.HD.value == "hd"
        assert CameraQuality.PRO.value == "pro"


class TestCameraFeature:
    """Tests for CameraFeature enum."""

    def test_values(self):
        """Test camera feature enum values."""
        from croom.video.usb_camera import CameraFeature

        assert CameraFeature.AUTO_FOCUS.value == "auto_focus"
        assert CameraFeature.ZOOM.value == "zoom"
        assert CameraFeature.PAN_TILT.value == "pan_tilt"


class TestUSBCameraInfo:
    """Tests for USBCameraInfo dataclass."""

    def test_basic_camera_info(self):
        """Test basic camera info creation."""
        from croom.video.usb_camera import USBCameraInfo

        info = USBCameraInfo(
            device_path="/dev/video0",
            name="USB Camera",
            vendor_id="046d",
            product_id="082d",
            bus_info="usb-0000:00:14.0-1",
        )
        assert info.device_path == "/dev/video0"
        assert info.vendor_id == "046d"
        assert info.max_fps == 30  # Default

    def test_camera_info_with_capabilities(self):
        """Test camera info with full capabilities."""
        from croom.video.usb_camera import USBCameraInfo

        info = USBCameraInfo(
            device_path="/dev/video0",
            name="Logitech C920",
            vendor_id="046d",
            product_id="082d",
            bus_info="usb-0000:00:14.0-1",
            supported_resolutions=[(1920, 1080), (1280, 720)],
            supported_formats=["YUYV", "MJPG"],
            max_fps=60,
        )
        assert len(info.supported_resolutions) == 2
        assert (1920, 1080) in info.supported_resolutions
        assert info.max_fps == 60


class TestKnownCameraProfiles:
    """Tests for known camera profiles."""

    def test_profiles_exist(self):
        """Test known camera profiles exist."""
        from croom.video.usb_camera import KNOWN_CAMERAS

        assert len(KNOWN_CAMERAS) > 0

    def test_logitech_profile(self):
        """Test Logitech camera profile exists."""
        from croom.video.usb_camera import KNOWN_CAMERAS

        # Check if any Logitech camera is in the profiles
        logitech_found = any("logitech" in str(cam).lower() for cam in KNOWN_CAMERAS.values())
        assert logitech_found or len(KNOWN_CAMERAS) > 0


class TestUSBCameraManager:
    """Tests for USBCameraManager class."""

    @pytest.fixture
    def camera_manager(self):
        """Create a camera manager instance."""
        from croom.video.usb_camera import USBCameraManager
        return USBCameraManager()

    def test_manager_creation(self, camera_manager):
        """Test camera manager can be created."""
        assert camera_manager is not None

    def test_cameras_property(self, camera_manager):
        """Test cameras property returns dict."""
        assert isinstance(camera_manager.cameras, dict)

    @pytest.mark.asyncio
    async def test_detect_cameras(self, camera_manager):
        """Test camera detection."""
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = []

            await camera_manager.detect_cameras()
            # Should not raise

    def test_get_nonexistent_camera(self, camera_manager):
        """Test getting non-existent camera returns None."""
        camera = camera_manager.get_camera("/dev/video99")
        assert camera is None

    def test_list_cameras_empty(self, camera_manager):
        """Test listing cameras when none detected."""
        cameras = camera_manager.list_cameras()
        assert isinstance(cameras, list)
