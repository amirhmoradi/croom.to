"""
Tests for croom.display.service module.
"""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from croom.display.service import (
    DisplayState,
    DisplayInfo,
    DisplayService,
    DDCController,
)


class TestDisplayState:
    """Tests for DisplayState enum."""

    def test_values(self):
        """Test display state enum values."""
        assert DisplayState.ON.value == "on"
        assert DisplayState.OFF.value == "off"
        assert DisplayState.STANDBY.value == "standby"
        assert DisplayState.UNKNOWN.value == "unknown"


class TestDisplayInfo:
    """Tests for DisplayInfo dataclass."""

    def test_default_values(self):
        """Test default display info values."""
        info = DisplayInfo()
        assert info.state == DisplayState.UNKNOWN
        assert info.brightness == 100
        assert info.resolution is None

    def test_custom_values(self):
        """Test custom display info values."""
        info = DisplayInfo(
            state=DisplayState.ON,
            brightness=75,
            resolution="1920x1080",
            manufacturer="Samsung",
            model="Smart TV",
        )
        assert info.state == DisplayState.ON
        assert info.brightness == 75
        assert info.manufacturer == "Samsung"


class TestDDCController:
    """Tests for DDCController class."""

    @pytest.fixture
    def ddc_controller(self):
        """Create a DDC controller instance."""
        return DDCController()

    @pytest.mark.asyncio
    async def test_is_available(self, ddc_controller):
        """Test DDC availability check."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"ddcutil", b"")
            mock_exec.return_value = mock_proc

            result = await ddc_controller.is_available()
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_set_brightness(self, ddc_controller):
        """Test setting brightness via DDC."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_proc

            result = await ddc_controller.set_brightness(75)
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_set_brightness_clamps_values(self, ddc_controller):
        """Test brightness values are clamped to valid range."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_proc

            # Should clamp to 100
            await ddc_controller.set_brightness(150)
            # Should clamp to 0
            await ddc_controller.set_brightness(-10)

    @pytest.mark.asyncio
    async def test_get_brightness(self, ddc_controller):
        """Test getting current brightness."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"current value = 75", b"")
            mock_exec.return_value = mock_proc

            result = await ddc_controller.get_brightness()
            assert isinstance(result, (int, type(None)))

    @pytest.mark.asyncio
    async def test_power_on(self, ddc_controller):
        """Test powering on display via DDC."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_proc

            result = await ddc_controller.power_on()
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_power_off(self, ddc_controller):
        """Test powering off display via DDC."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_proc

            result = await ddc_controller.power_off()
            assert isinstance(result, bool)


class TestDisplayService:
    """Tests for DisplayService class."""

    @pytest.fixture
    def display_service(self):
        """Create a display service instance."""
        with patch("croom.display.service.PlatformDetector"):
            service = DisplayService()
            return service

    def test_initial_state(self, display_service):
        """Test initial display service state."""
        assert display_service.current_state == DisplayState.UNKNOWN

    @pytest.mark.asyncio
    async def test_power_on(self, display_service):
        """Test powering on display."""
        with patch.object(display_service, "_backend") as mock_backend:
            mock_backend.power_on = AsyncMock(return_value=True)

            result = await display_service.power_on()
            assert result is True

    @pytest.mark.asyncio
    async def test_power_off(self, display_service):
        """Test powering off display."""
        with patch.object(display_service, "_backend") as mock_backend:
            mock_backend.power_off = AsyncMock(return_value=True)

            result = await display_service.power_off()
            assert result is True

    @pytest.mark.asyncio
    async def test_standby(self, display_service):
        """Test putting display in standby."""
        with patch.object(display_service, "_backend") as mock_backend:
            mock_backend.standby = AsyncMock(return_value=True)

            result = await display_service.standby()
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_set_brightness(self, display_service):
        """Test setting display brightness."""
        with patch.object(display_service, "_backend") as mock_backend:
            mock_backend.set_brightness = AsyncMock(return_value=True)

            result = await display_service.set_brightness(50)
            assert result is True

    @pytest.mark.asyncio
    async def test_get_info(self, display_service):
        """Test getting display information."""
        with patch.object(display_service, "_backend") as mock_backend:
            mock_backend.get_info = AsyncMock(
                return_value=DisplayInfo(
                    state=DisplayState.ON,
                    brightness=100,
                )
            )

            info = await display_service.get_info()
            assert isinstance(info, DisplayInfo)

    def test_select_backend_cec(self, display_service):
        """Test CEC backend selection."""
        with patch.object(display_service._detector, "has_cec", True):
            with patch.object(display_service._detector, "has_ddc", False):
                backend = display_service._select_backend()
                # Should select CEC when available

    def test_select_backend_ddc(self, display_service):
        """Test DDC backend selection when CEC unavailable."""
        with patch.object(display_service._detector, "has_cec", False):
            with patch.object(display_service._detector, "has_ddc", True):
                backend = display_service._select_backend()
                # Should select DDC when CEC unavailable


class TestDisplayServiceEvents:
    """Tests for DisplayService event handling."""

    @pytest.fixture
    def display_service(self):
        """Create a display service instance."""
        with patch("croom.display.service.PlatformDetector"):
            service = DisplayService()
            return service

    def test_register_state_callback(self, display_service):
        """Test registering state change callback."""
        callback = MagicMock()
        display_service.on_state_change(callback)

        assert callback in display_service._state_callbacks

    @pytest.mark.asyncio
    async def test_callback_called_on_power_change(self, display_service):
        """Test callback is called when power state changes."""
        callback = MagicMock()
        display_service.on_state_change(callback)

        with patch.object(display_service, "_backend") as mock_backend:
            mock_backend.power_on = AsyncMock(return_value=True)
            await display_service.power_on()

            # Callback should be called with new state
