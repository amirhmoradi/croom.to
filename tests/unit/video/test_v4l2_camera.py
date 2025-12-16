"""
Tests for croom.video.camera V4L2Camera and v4l2_ioctl module.
"""

import asyncio
import ctypes
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
import numpy as np

from croom.video.v4l2_ioctl import (
    V4L2_BUF_TYPE_VIDEO_CAPTURE,
    V4L2_MEMORY_MMAP,
    V4L2_PIX_FMT_MJPEG,
    V4L2_PIX_FMT_YUYV,
    V4L2_CID_BRIGHTNESS,
    V4L2_CID_CONTRAST,
    V4L2_CID_SATURATION,
    V4L2_CID_ZOOM_ABSOLUTE,
    VIDIOC_QUERYCAP,
    VIDIOC_S_FMT,
    VIDIOC_REQBUFS,
    VIDIOC_QBUF,
    VIDIOC_DQBUF,
    VIDIOC_STREAMON,
    VIDIOC_STREAMOFF,
    VIDIOC_S_CTRL,
    VIDIOC_G_CTRL,
    v4l2_capability,
    v4l2_format,
    v4l2_requestbuffers,
    v4l2_buffer,
    v4l2_control,
)
from croom.video.camera import (
    V4L2Camera,
    CameraInfo,
    Resolution,
    CameraBackend,
    RESOLUTION_1080P,
    RESOLUTION_720P,
    RESOLUTION_480P,
)


class TestV4L2Constants:
    """Tests for V4L2 constants."""

    def test_buf_type_constants(self):
        """Test buffer type constants."""
        assert V4L2_BUF_TYPE_VIDEO_CAPTURE == 1
        assert V4L2_MEMORY_MMAP == 1

    def test_pixel_format_constants(self):
        """Test pixel format constants."""
        # MJPEG = 'MJPG' = 0x47504A4D
        assert V4L2_PIX_FMT_MJPEG == 0x47504A4D
        # YUYV = 'YUYV' = 0x56595559
        assert V4L2_PIX_FMT_YUYV == 0x56595559

    def test_control_id_constants(self):
        """Test control ID constants."""
        assert V4L2_CID_BRIGHTNESS == 0x00980900
        assert V4L2_CID_CONTRAST == 0x00980901
        assert V4L2_CID_SATURATION == 0x00980902


class TestV4L2Structures:
    """Tests for V4L2 ctypes structures."""

    def test_capability_structure(self):
        """Test v4l2_capability structure."""
        cap = v4l2_capability()

        # Check structure fields exist
        assert hasattr(cap, 'driver')
        assert hasattr(cap, 'card')
        assert hasattr(cap, 'bus_info')
        assert hasattr(cap, 'version')
        assert hasattr(cap, 'capabilities')

    def test_format_structure(self):
        """Test v4l2_format structure."""
        fmt = v4l2_format()

        assert hasattr(fmt, 'type')
        assert hasattr(fmt, 'fmt')

    def test_requestbuffers_structure(self):
        """Test v4l2_requestbuffers structure."""
        req = v4l2_requestbuffers()

        assert hasattr(req, 'count')
        assert hasattr(req, 'type')
        assert hasattr(req, 'memory')

    def test_buffer_structure(self):
        """Test v4l2_buffer structure."""
        buf = v4l2_buffer()

        assert hasattr(buf, 'index')
        assert hasattr(buf, 'type')
        assert hasattr(buf, 'bytesused')
        assert hasattr(buf, 'flags')
        assert hasattr(buf, 'memory')

    def test_control_structure(self):
        """Test v4l2_control structure."""
        ctrl = v4l2_control()

        assert hasattr(ctrl, 'id')
        assert hasattr(ctrl, 'value')

        # Test setting values
        ctrl.id = V4L2_CID_BRIGHTNESS
        ctrl.value = 128
        assert ctrl.id == V4L2_CID_BRIGHTNESS
        assert ctrl.value == 128


class TestResolution:
    """Tests for Resolution dataclass."""

    def test_creation(self):
        """Test creating a resolution."""
        res = Resolution(width=1920, height=1080)

        assert res.width == 1920
        assert res.height == 1080

    def test_aspect_ratio(self):
        """Test aspect ratio property."""
        res = Resolution(width=1920, height=1080)

        assert abs(res.aspect_ratio - (16 / 9)) < 0.01

    def test_pixels(self):
        """Test pixels property."""
        res = Resolution(width=1920, height=1080)

        assert res.pixels == 1920 * 1080

    def test_str(self):
        """Test string representation."""
        res = Resolution(width=1920, height=1080)

        assert str(res) == "1920x1080"

    def test_from_string(self):
        """Test creating from string."""
        res = Resolution.from_string("1920x1080")

        assert res.width == 1920
        assert res.height == 1080


class TestCameraInfo:
    """Tests for CameraInfo dataclass."""

    def test_creation(self):
        """Test creating camera info."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )

        assert info.id == "0"
        assert info.name == "Test Camera"
        assert info.backend == CameraBackend.V4L2
        assert info.device_path == "/dev/video0"

    def test_default_values(self):
        """Test default values."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.OPENCV,
        )

        assert info.device_path == ""
        assert info.resolutions == []
        assert info.max_fps == 30
        assert info.has_autofocus is False

    def test_best_resolution(self):
        """Test best resolution property."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            resolutions=[RESOLUTION_720P, RESOLUTION_1080P, RESOLUTION_480P],
        )

        best = info.best_resolution
        assert best.width == 1920
        assert best.height == 1080

    def test_best_resolution_default(self):
        """Test best resolution default when no resolutions."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
        )

        best = info.best_resolution
        assert best == RESOLUTION_1080P


class TestV4L2Camera:
    """Tests for V4L2Camera class."""

    def test_init(self):
        """Test V4L2Camera initialization."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )

        camera = V4L2Camera(info)

        assert camera.info.device_path == "/dev/video0"
        assert camera._resolution == RESOLUTION_1080P
        assert camera._fps == 30

    def test_init_with_custom_resolution(self):
        """Test V4L2Camera with custom resolution."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )

        camera = V4L2Camera(info)
        camera._resolution = RESOLUTION_720P

        assert camera._resolution.width == 1280
        assert camera._resolution.height == 720

    def test_is_running_initial(self):
        """Test is_running initial state."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
        )

        camera = V4L2Camera(info)
        assert camera.is_running is False

    @pytest.mark.asyncio
    async def test_open_device_not_found(self):
        """Test opening non-existent device."""
        info = CameraInfo(
            id="99",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video99",
        )
        camera = V4L2Camera(info)

        with patch("os.open", side_effect=FileNotFoundError()):
            result = await camera.open()
            assert result is False

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing camera."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )
        camera = V4L2Camera(info)
        camera._fd = 3
        camera._buffers = [{'mmap': MagicMock()}, {'mmap': MagicMock()}]

        with patch("os.close"):
            await camera.close()
            assert camera._fd is None
            assert camera._buffers == []

    @pytest.mark.asyncio
    async def test_start(self):
        """Test starting capture."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )
        camera = V4L2Camera(info)
        camera._fd = 3
        camera._running = False
        camera._buffers = [{'mmap': MagicMock()}, {'mmap': MagicMock()}]
        camera._frame_queue = asyncio.Queue()

        with patch("fcntl.ioctl"):
            with patch("ctypes.c_int"):
                await camera.start()
                assert camera._running is True

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stopping capture."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )
        camera = V4L2Camera(info)
        camera._fd = 3
        camera._running = True
        camera._capture_task = None

        with patch("fcntl.ioctl"):
            with patch("ctypes.c_int"):
                await camera.stop()
                assert camera._running is False

    @pytest.mark.asyncio
    async def test_set_control(self):
        """Test setting V4L2 control."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )
        camera = V4L2Camera(info)
        camera._fd = 3

        with patch("fcntl.ioctl", return_value=0):
            result = await camera.set_control(V4L2_CID_BRIGHTNESS, 128)
            assert result is True

    @pytest.mark.asyncio
    async def test_set_control_failure(self):
        """Test setting control failure."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )
        camera = V4L2Camera(info)
        camera._fd = 3

        with patch("fcntl.ioctl", side_effect=OSError()):
            result = await camera.set_control(V4L2_CID_BRIGHTNESS, 128)
            assert result is False

    @pytest.mark.asyncio
    async def test_get_control(self):
        """Test getting V4L2 control."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )
        camera = V4L2Camera(info)
        camera._fd = 3

        def mock_ioctl(fd, request, arg):
            if hasattr(arg, 'value'):
                arg.value = 128
            return 0

        with patch("fcntl.ioctl", side_effect=mock_ioctl):
            value = await camera.get_control(V4L2_CID_BRIGHTNESS)
            assert value == 128

    @pytest.mark.asyncio
    async def test_get_control_failure(self):
        """Test getting control failure."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )
        camera = V4L2Camera(info)
        camera._fd = 3

        with patch("fcntl.ioctl", side_effect=OSError()):
            value = await camera.get_control(V4L2_CID_BRIGHTNESS)
            assert value is None

    @pytest.mark.asyncio
    async def test_read_not_running(self):
        """Test reading frame when not running."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )
        camera = V4L2Camera(info)
        camera._running = False

        frame = await camera.read()
        assert frame is None

    def test_resolution_property(self):
        """Test resolution property."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )
        camera = V4L2Camera(info)
        camera._resolution = Resolution(1280, 720)

        assert camera.resolution.width == 1280
        assert camera.resolution.height == 720

    def test_fps_property(self):
        """Test fps property."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )
        camera = V4L2Camera(info)
        camera._fps = 60

        assert camera.fps == 60

    def test_on_frame_callback(self):
        """Test frame callback registration."""
        info = CameraInfo(
            id="0",
            name="Test Camera",
            backend=CameraBackend.V4L2,
            device_path="/dev/video0",
        )
        camera = V4L2Camera(info)

        callback = MagicMock()
        camera.on_frame(callback)

        assert callback in camera._callbacks


class TestCameraBackend:
    """Tests for CameraBackend enum."""

    def test_values(self):
        """Test camera backend enum values."""
        assert CameraBackend.LIBCAMERA.value == "libcamera"
        assert CameraBackend.V4L2.value == "v4l2"
        assert CameraBackend.OPENCV.value == "opencv"
        assert CameraBackend.AUTO.value == "auto"
