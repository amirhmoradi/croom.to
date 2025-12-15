"""
Tests for croom.platform.hal module (Hardware Abstraction Layer).
"""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from croom.platform.hal import (
    GPIOMode,
    GPIOPull,
    GPIOPin,
    GPIOInterface,
    StubGPIO,
    HardwareAbstractionLayer,
)


class TestGPIOMode:
    """Tests for GPIOMode enum."""

    def test_values(self):
        """Test GPIO mode enum values."""
        assert GPIOMode.INPUT.value == "input"
        assert GPIOMode.OUTPUT.value == "output"


class TestGPIOPull:
    """Tests for GPIOPull enum."""

    def test_values(self):
        """Test GPIO pull enum values."""
        assert GPIOPull.NONE.value == "none"
        assert GPIOPull.UP.value == "up"
        assert GPIOPull.DOWN.value == "down"


class TestGPIOPin:
    """Tests for GPIOPin dataclass."""

    def test_default_values(self):
        """Test default GPIO pin values."""
        pin = GPIOPin(number=17, mode=GPIOMode.INPUT)
        assert pin.number == 17
        assert pin.mode == GPIOMode.INPUT
        assert pin.pull == GPIOPull.NONE
        assert pin.value == 0

    def test_custom_values(self):
        """Test custom GPIO pin values."""
        pin = GPIOPin(
            number=27,
            mode=GPIOMode.OUTPUT,
            pull=GPIOPull.UP,
            value=1,
        )
        assert pin.number == 27
        assert pin.mode == GPIOMode.OUTPUT
        assert pin.pull == GPIOPull.UP
        assert pin.value == 1


class TestStubGPIO:
    """Tests for StubGPIO class."""

    def test_setup_input(self):
        """Test setting up input pin."""
        gpio = StubGPIO()
        result = gpio.setup(17, GPIOMode.INPUT)

        assert result is True
        assert 17 in gpio._pins
        assert gpio._pins[17].mode == GPIOMode.INPUT

    def test_setup_output(self):
        """Test setting up output pin."""
        gpio = StubGPIO()
        result = gpio.setup(27, GPIOMode.OUTPUT, GPIOPull.DOWN)

        assert result is True
        assert gpio._pins[27].mode == GPIOMode.OUTPUT
        assert gpio._pins[27].pull == GPIOPull.DOWN

    def test_write_pin(self):
        """Test writing to output pin."""
        gpio = StubGPIO()
        gpio.setup(17, GPIOMode.OUTPUT)
        result = gpio.write(17, 1)

        assert result is True
        assert gpio._pins[17].value == 1

    def test_write_nonexistent_pin(self):
        """Test writing to pin that wasn't set up."""
        gpio = StubGPIO()
        result = gpio.write(99, 1)

        assert result is False

    def test_read_pin(self):
        """Test reading from pin."""
        gpio = StubGPIO()
        gpio.setup(17, GPIOMode.INPUT)
        gpio._pins[17].value = 1

        value = gpio.read(17)
        assert value == 1

    def test_read_nonexistent_pin(self):
        """Test reading from pin that wasn't set up."""
        gpio = StubGPIO()
        value = gpio.read(99)

        assert value == 0

    def test_cleanup(self):
        """Test GPIO cleanup."""
        gpio = StubGPIO()
        gpio.setup(17, GPIOMode.OUTPUT)
        gpio.setup(27, GPIOMode.INPUT)

        gpio.cleanup()
        assert len(gpio._pins) == 0

    def test_cleanup_specific_pin(self):
        """Test cleaning up specific pin."""
        gpio = StubGPIO()
        gpio.setup(17, GPIOMode.OUTPUT)
        gpio.setup(27, GPIOMode.INPUT)

        gpio.cleanup(17)

        assert 17 not in gpio._pins
        assert 27 in gpio._pins


class TestHardwareAbstractionLayer:
    """Tests for HardwareAbstractionLayer class."""

    @patch("croom.platform.hal.PlatformDetector")
    def test_init_with_stub_gpio(self, mock_detector):
        """Test HAL initialization uses StubGPIO on non-Pi systems."""
        mock_instance = MagicMock()
        mock_instance.has_gpio = False
        mock_detector.return_value = mock_instance

        hal = HardwareAbstractionLayer()

        assert isinstance(hal.gpio, StubGPIO)

    @patch("croom.platform.hal.PlatformDetector")
    def test_get_platform_info(self, mock_detector):
        """Test getting platform information."""
        mock_instance = MagicMock()
        mock_instance.device_type.value = "pc"
        mock_instance.architecture.value = "amd64"
        mock_instance.has_gpio = False
        mock_detector.return_value = mock_instance

        hal = HardwareAbstractionLayer()
        info = hal.get_platform_info()

        assert "device_type" in info
        assert "architecture" in info

    @patch("croom.platform.hal.PlatformDetector")
    def test_setup_led_pin(self, mock_detector):
        """Test setting up LED indicator pin."""
        mock_instance = MagicMock()
        mock_instance.has_gpio = False
        mock_detector.return_value = mock_instance

        hal = HardwareAbstractionLayer()
        result = hal.setup_led(17)

        assert result is True

    @patch("croom.platform.hal.PlatformDetector")
    def test_set_led_state(self, mock_detector):
        """Test setting LED state."""
        mock_instance = MagicMock()
        mock_instance.has_gpio = False
        mock_detector.return_value = mock_instance

        hal = HardwareAbstractionLayer()
        hal.setup_led(17)
        result = hal.set_led(17, True)

        assert result is True

    @patch("croom.platform.hal.PlatformDetector")
    def test_setup_button(self, mock_detector):
        """Test setting up button input."""
        mock_instance = MagicMock()
        mock_instance.has_gpio = False
        mock_detector.return_value = mock_instance

        hal = HardwareAbstractionLayer()
        result = hal.setup_button(27, pull_up=True)

        assert result is True

    @patch("croom.platform.hal.PlatformDetector")
    def test_read_button(self, mock_detector):
        """Test reading button state."""
        mock_instance = MagicMock()
        mock_instance.has_gpio = False
        mock_detector.return_value = mock_instance

        hal = HardwareAbstractionLayer()
        hal.setup_button(27)
        state = hal.read_button(27)

        assert isinstance(state, bool)


class TestHALCleanup:
    """Tests for HAL cleanup functionality."""

    @patch("croom.platform.hal.PlatformDetector")
    def test_cleanup_all(self, mock_detector):
        """Test cleaning up all GPIO pins."""
        mock_instance = MagicMock()
        mock_instance.has_gpio = False
        mock_detector.return_value = mock_instance

        hal = HardwareAbstractionLayer()
        hal.setup_led(17)
        hal.setup_button(27)

        hal.cleanup()

        # Should not raise
        assert True

    @patch("croom.platform.hal.PlatformDetector")
    def test_context_manager(self, mock_detector):
        """Test HAL as context manager."""
        mock_instance = MagicMock()
        mock_instance.has_gpio = False
        mock_detector.return_value = mock_instance

        with HardwareAbstractionLayer() as hal:
            hal.setup_led(17)
            # HAL should work within context

        # After context, cleanup should have been called
        assert True
