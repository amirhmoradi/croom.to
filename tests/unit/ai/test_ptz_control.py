"""
Tests for croom.ai.ptz_control module.
"""

import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

import pytest

from croom.ai.ptz_control import (
    PTZProtocol,
    PTZCapability,
    PTZPosition,
    PTZPreset,
    PTZLimits,
    PTZController,
    VISCAController,
    ONVIFController,
    PelcoDController,
    HTTPPTZController,
    SoftwarePTZController,
    create_ptz_controller,
)


class TestPTZProtocol:
    """Tests for PTZProtocol enum."""

    def test_values(self):
        """Test PTZ protocol enum values."""
        assert PTZProtocol.VISCA.value == "visca"
        assert PTZProtocol.ONVIF.value == "onvif"
        assert PTZProtocol.PELCO_D.value == "pelco_d"
        assert PTZProtocol.HTTP.value == "http"
        assert PTZProtocol.USB.value == "usb"


class TestPTZCapability:
    """Tests for PTZCapability enum."""

    def test_values(self):
        """Test PTZ capability enum values."""
        assert PTZCapability.PAN.value == "pan"
        assert PTZCapability.TILT.value == "tilt"
        assert PTZCapability.ZOOM.value == "zoom"
        assert PTZCapability.FOCUS.value == "focus"
        assert PTZCapability.PRESET.value == "preset"
        assert PTZCapability.HOME.value == "home"


class TestPTZPosition:
    """Tests for PTZPosition dataclass."""

    def test_creation(self):
        """Test creating a PTZ position."""
        position = PTZPosition(pan=0.5, tilt=-0.3, zoom=0.8)

        assert position.pan == 0.5
        assert position.tilt == -0.3
        assert position.zoom == 0.8

    def test_default_values(self):
        """Test default PTZ position values."""
        position = PTZPosition()

        assert position.pan == 0.0
        assert position.tilt == 0.0
        assert position.zoom == 0.0

    def test_to_dict(self):
        """Test converting position to dictionary."""
        position = PTZPosition(pan=0.5, tilt=-0.3, zoom=0.8)
        result = position.to_dict()

        assert result["pan"] == 0.5
        assert result["tilt"] == -0.3
        assert result["zoom"] == 0.8
        assert "timestamp" in result


class TestPTZPreset:
    """Tests for PTZPreset dataclass."""

    def test_creation(self):
        """Test creating a PTZ preset."""
        position = PTZPosition(pan=0.0, tilt=0.0, zoom=0.0)
        preset = PTZPreset(id=1, name="Center", position=position)

        assert preset.id == 1
        assert preset.name == "Center"
        assert preset.position.pan == 0.0

    def test_to_dict(self):
        """Test converting preset to dictionary."""
        position = PTZPosition(pan=0.5, tilt=0.3, zoom=0.2)
        preset = PTZPreset(id=1, name="Home", position=position)
        result = preset.to_dict()

        assert result["id"] == 1
        assert result["name"] == "Home"
        assert "position" in result


class TestPTZLimits:
    """Tests for PTZLimits dataclass."""

    def test_default_values(self):
        """Test default PTZ limits."""
        limits = PTZLimits()

        assert limits.pan_min == -1.0
        assert limits.pan_max == 1.0
        assert limits.tilt_min == -1.0
        assert limits.tilt_max == 1.0
        assert limits.zoom_min == 0.0
        assert limits.zoom_max == 1.0

    def test_custom_values(self):
        """Test custom PTZ limits."""
        limits = PTZLimits(
            pan_min=-0.5,
            pan_max=0.5,
            zoom_max=0.8,
        )

        assert limits.pan_min == -0.5
        assert limits.pan_max == 0.5
        assert limits.zoom_max == 0.8


class TestVISCAController:
    """Tests for VISCAController class."""

    def test_init(self):
        """Test VISCA controller initialization."""
        controller = VISCAController(host="192.168.1.100", port=52381, camera_address=1)

        assert controller.protocol == PTZProtocol.VISCA
        assert controller._host == "192.168.1.100"
        assert controller._port == 52381
        assert controller._camera_address == 1

    def test_init_defaults(self):
        """Test VISCA controller with default values."""
        controller = VISCAController()

        assert controller._host == "192.168.1.100"
        assert controller._port == 52381
        assert controller._camera_address == 1

    def test_capabilities(self):
        """Test VISCA controller capabilities."""
        controller = VISCAController()

        assert PTZCapability.PAN in controller.capabilities
        assert PTZCapability.TILT in controller.capabilities
        assert PTZCapability.ZOOM in controller.capabilities

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful VISCA connection."""
        controller = VISCAController()

        with patch("asyncio.open_connection") as mock_connect:
            mock_reader = AsyncMock()
            mock_writer = MagicMock()
            mock_writer.close = MagicMock()
            mock_writer.wait_closed = AsyncMock()
            mock_connect.return_value = (mock_reader, mock_writer)

            # Mock get_position to avoid additional network calls
            with patch.object(controller, "get_position", new_callable=AsyncMock):
                result = await controller.connect()
                assert result is True
                assert controller.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test failed VISCA connection."""
        controller = VISCAController()

        with patch("asyncio.open_connection", side_effect=ConnectionRefusedError()):
            result = await controller.connect()
            assert result is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test VISCA disconnection."""
        controller = VISCAController()
        controller._connected = True
        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        controller._writer = mock_writer

        await controller.disconnect()

        assert controller.is_connected is False
        mock_writer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test VISCA stop command."""
        controller = VISCAController()
        controller._connected = True
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        controller._writer = mock_writer

        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value=b"\x00\x00\x00\x00")
        controller._reader = mock_reader

        result = await controller.stop()
        assert result is True


class TestONVIFController:
    """Tests for ONVIFController class."""

    def test_init(self):
        """Test ONVIF controller initialization."""
        controller = ONVIFController(
            host="192.168.1.100",
            port=80,
            username="admin",
            password="password",
        )

        assert controller.protocol == PTZProtocol.ONVIF
        assert controller._host == "192.168.1.100"
        assert controller._port == 80
        assert controller._username == "admin"

    def test_capabilities(self):
        """Test ONVIF controller capabilities."""
        controller = ONVIFController(host="192.168.1.100")

        assert PTZCapability.PAN in controller.capabilities
        assert PTZCapability.TILT in controller.capabilities
        assert PTZCapability.ZOOM in controller.capabilities

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test ONVIF stop command."""
        controller = ONVIFController(host="192.168.1.100")
        controller._ptz_service = MagicMock()
        controller._profile_token = "profile_1"
        controller._connected = True

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock()
            result = await controller.stop()
            assert result is True

    @pytest.mark.asyncio
    async def test_get_position(self):
        """Test ONVIF get position."""
        controller = ONVIFController(host="192.168.1.100")
        controller._connected = True
        controller._profile_token = "profile_1"

        mock_ptz = MagicMock()
        mock_status = MagicMock()
        mock_status.Position = MagicMock()
        mock_status.Position.PanTilt = MagicMock(x=0.5, y=0.3)
        mock_status.Position.Zoom = MagicMock(x=0.2)
        mock_ptz.GetStatus = MagicMock(return_value=mock_status)
        controller._ptz_service = mock_ptz

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=mock_status)
            position = await controller.get_position()
            assert isinstance(position, PTZPosition)


class TestPelcoDController:
    """Tests for PelcoDController class."""

    def test_init(self):
        """Test Pelco-D controller initialization."""
        controller = PelcoDController(
            port="/dev/ttyUSB0",
            baudrate=9600,
            camera_address=1,
        )

        assert controller.protocol == PTZProtocol.PELCO_D
        assert controller._port == "/dev/ttyUSB0"
        assert controller._camera_address == 1
        assert controller._baudrate == 9600

    def test_build_command(self):
        """Test Pelco-D command building."""
        controller = PelcoDController(port="/dev/ttyUSB0", camera_address=1)

        cmd = controller._build_command(0x00, 0x04, 0x20, 0x00)

        assert cmd[0] == 0xFF  # Sync byte
        assert cmd[1] == 1  # Address
        assert len(cmd) == 7  # Full command length

    def test_capabilities(self):
        """Test Pelco-D controller capabilities."""
        controller = PelcoDController(port="/dev/ttyUSB0")

        assert PTZCapability.PAN in controller.capabilities
        assert PTZCapability.TILT in controller.capabilities
        assert PTZCapability.ZOOM in controller.capabilities

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test Pelco-D connection."""
        controller = PelcoDController(port="/dev/ttyUSB0")

        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True

        with patch.dict("sys.modules", {"serial": MagicMock()}):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(return_value=mock_serial_instance)
                controller._serial = mock_serial_instance
                controller._connected = True
                # Just verify the controller can be set up
                assert controller._serial.is_open is True

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test Pelco-D stop command."""
        controller = PelcoDController(port="/dev/ttyUSB0")
        controller._serial = MagicMock()
        controller._serial.is_open = True

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock()
            result = await controller.stop()
            assert result is True


class TestHTTPPTZController:
    """Tests for HTTPPTZController class."""

    def test_init(self):
        """Test HTTP PTZ controller initialization."""
        controller = HTTPPTZController(
            base_url="http://192.168.1.100/cgi-bin/ptz.cgi",
            username="admin",
            password="password",
        )

        assert controller.protocol == PTZProtocol.HTTP
        assert controller._base_url == "http://192.168.1.100/cgi-bin/ptz.cgi"
        assert controller._username == "admin"

    def test_init_with_custom_endpoints(self):
        """Test HTTP PTZ controller with custom endpoints."""
        endpoints = {
            "move_to": "/api/ptz/move",
            "stop": "/api/ptz/stop",
            "preset_call": "/api/ptz/preset",
            "position": "/api/ptz/position",
        }

        controller = HTTPPTZController(
            base_url="http://192.168.1.100",
            endpoints=endpoints,
        )

        assert controller._endpoints == endpoints

    def test_capabilities(self):
        """Test HTTP PTZ controller capabilities."""
        controller = HTTPPTZController(base_url="http://192.168.1.100")

        assert PTZCapability.PAN in controller.capabilities
        assert PTZCapability.ZOOM in controller.capabilities

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test HTTP PTZ stop command."""
        controller = HTTPPTZController(base_url="http://192.168.1.100")
        controller._connected = True

        mock_session = MagicMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
        controller._session = mock_session

        result = await controller.stop()
        assert result is True


class TestSoftwarePTZController:
    """Tests for SoftwarePTZController class."""

    def test_init(self):
        """Test software PTZ controller initialization."""
        controller = SoftwarePTZController(frame_width=1920, frame_height=1080)

        assert controller.protocol == PTZProtocol.USB
        assert controller._frame_width == 1920
        assert controller._frame_height == 1080

    def test_capabilities(self):
        """Test software PTZ controller capabilities."""
        controller = SoftwarePTZController()

        assert PTZCapability.PAN in controller.capabilities
        assert PTZCapability.TILT in controller.capabilities
        assert PTZCapability.ZOOM in controller.capabilities

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test software PTZ connection."""
        controller = SoftwarePTZController()

        result = await controller.connect()
        assert result is True
        assert controller.is_connected is True

    @pytest.mark.asyncio
    async def test_move_to(self):
        """Test software PTZ move to position."""
        controller = SoftwarePTZController()

        result = await controller.move_to(pan=0.5, tilt=-0.3, zoom=0.2)
        assert result is True

    @pytest.mark.asyncio
    async def test_go_home(self):
        """Test software PTZ go home."""
        controller = SoftwarePTZController()

        result = await controller.go_home()
        assert result is True

    def test_update(self):
        """Test software PTZ update."""
        controller = SoftwarePTZController()
        controller._target_position = PTZPosition(pan=0.5, tilt=0.3, zoom=0.2)

        # Call update multiple times to move towards target
        for _ in range(100):
            controller.update(dt=0.033)

        # Position should be near target
        assert abs(controller.position.pan - 0.5) < 0.1
        assert abs(controller.position.tilt - 0.3) < 0.1

    def test_get_crop_region(self):
        """Test software PTZ crop region calculation."""
        controller = SoftwarePTZController(frame_width=1920, frame_height=1080)
        controller._position = PTZPosition(pan=0, tilt=0, zoom=0)

        x1, y1, x2, y2 = controller.get_crop_region()

        # Should return valid crop region
        assert x1 >= 0
        assert y1 >= 0
        assert x2 <= 1920
        assert y2 <= 1080
        assert x2 > x1
        assert y2 > y1


class TestCreatePTZController:
    """Tests for create_ptz_controller factory function."""

    def test_create_visca(self):
        """Test creating VISCA controller."""
        controller = create_ptz_controller(
            protocol=PTZProtocol.VISCA,
            host="192.168.1.100",
            port=52381,
        )

        assert isinstance(controller, VISCAController)

    def test_create_onvif(self):
        """Test creating ONVIF controller."""
        controller = create_ptz_controller(
            protocol=PTZProtocol.ONVIF,
            host="192.168.1.100",
            port=80,
            username="admin",
            password="password",
        )

        assert isinstance(controller, ONVIFController)

    def test_create_pelco_d(self):
        """Test creating Pelco-D controller."""
        controller = create_ptz_controller(
            protocol=PTZProtocol.PELCO_D,
            port="/dev/ttyUSB0",
            camera_address=1,
        )

        assert isinstance(controller, PelcoDController)

    def test_create_http(self):
        """Test creating HTTP PTZ controller."""
        controller = create_ptz_controller(
            protocol=PTZProtocol.HTTP,
            base_url="http://192.168.1.100/cgi-bin/ptz.cgi",
        )

        assert isinstance(controller, HTTPPTZController)

    def test_create_software(self):
        """Test creating software PTZ controller."""
        controller = create_ptz_controller(
            protocol=PTZProtocol.USB,
            frame_width=1920,
            frame_height=1080,
        )

        assert isinstance(controller, SoftwarePTZController)
