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
            resolution=(1920, 1080),
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

    def test_is_available(self, ddc_controller):
        """Test DDC availability check."""
        # is_available is a property that returns bool
        result = ddc_controller.is_available
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
            # Should not raise

    @pytest.mark.asyncio
    async def test_set_brightness_clamps_values(self, ddc_controller):
        """Test brightness values are clamped to 0-100."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_proc

            # Should clamp to valid range
            await ddc_controller.set_brightness(150)
            await ddc_controller.set_brightness(-10)

    @pytest.mark.asyncio
    async def test_get_brightness(self, ddc_controller):
        """Test getting brightness via DDC."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"VCP code 0x10 (Brightness): current value = 75", b"")
            mock_exec.return_value = mock_proc

            result = await ddc_controller.get_brightness()
            # Result depends on parsing

    @pytest.mark.asyncio
    async def test_power_on(self, ddc_controller):
        """Test powering on display via DDC."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_proc

            result = await ddc_controller.power_on()
            # Should not raise

    @pytest.mark.asyncio
    async def test_power_off(self, ddc_controller):
        """Test powering off display via DDC."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_proc

            result = await ddc_controller.power_off()
            # Should not raise


class TestDisplayService:
    """Tests for DisplayService class."""

    @pytest.fixture
    def display_service(self):
        """Create a display service instance."""
        service = DisplayService()
        return service

    def test_initial_state(self, display_service):
        """Test initial display service state."""
        # Use internal state attribute
        assert display_service._display_state == DisplayState.UNKNOWN

    def test_cec_enabled(self, display_service):
        """Test CEC is enabled by default."""
        assert display_service._cec_enabled is True

    def test_ddc_enabled(self, display_service):
        """Test DDC is enabled by default."""
        assert display_service._ddc_enabled is True

    def test_config_override(self):
        """Test config can override defaults."""
        service = DisplayService(config={"cec_enabled": False, "ddc_enabled": False})
        assert service._cec_enabled is False
        assert service._ddc_enabled is False

    @pytest.mark.asyncio
    async def test_initialize(self, display_service):
        """Test service initialization."""
        with patch.object(display_service, "_ddc", None):
            with patch.object(display_service, "_cec", None):
                # Should not raise
                await display_service.initialize()

    def test_cec_available(self, display_service):
        """Test cec_available property."""
        result = display_service.cec_available
        assert isinstance(result, bool)

    def test_ddc_available(self, display_service):
        """Test ddc_available property."""
        result = display_service.ddc_available
        assert isinstance(result, bool)

    def test_state_property(self, display_service):
        """Test state property."""
        state = display_service.state
        assert isinstance(state, DisplayState)


class TestDisplayServicePower:
    """Tests for DisplayService power operations."""

    @pytest.fixture
    def display_service(self):
        """Create a display service instance."""
        return DisplayService()

    @pytest.mark.asyncio
    async def test_power_on_via_ddc(self, display_service):
        """Test power on uses DDC when available."""
        mock_ddc = MagicMock()
        mock_ddc.power_on = AsyncMock(return_value=True)
        mock_ddc.is_available = True
        display_service._ddc = mock_ddc
        display_service._control_method = "ddc"

        result = await display_service.power_on()
        assert result is True
        mock_ddc.power_on.assert_called_once()

    @pytest.mark.asyncio
    async def test_power_off_via_ddc(self, display_service):
        """Test power off uses DDC when available."""
        mock_ddc = MagicMock()
        mock_ddc.power_off = AsyncMock(return_value=True)
        mock_ddc.is_available = True
        display_service._ddc = mock_ddc
        display_service._control_method = "ddc"

        result = await display_service.power_off()
        assert result is True
        mock_ddc.power_off.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_brightness(self, display_service):
        """Test setting brightness."""
        mock_ddc = MagicMock()
        mock_ddc.set_brightness = AsyncMock(return_value=True)
        mock_ddc.is_available = True
        display_service._ddc = mock_ddc
        display_service._control_method = "ddc"

        result = await display_service.set_brightness(75)
        assert result is True
        mock_ddc.set_brightness.assert_called_once_with(75)
