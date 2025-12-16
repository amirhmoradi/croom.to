"""
Tests for croom.platform.hal module (Hardware Abstraction Layer).
"""

import time
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from croom.platform.hal import (
    GPIOMode,
    GPIOPull,
    GPIOEdge,
    GPIOPin,
    GPIOInterface,
    StubGPIO,
    LinuxGPIO,
    SoftwarePWM,
    GPIOEventMonitor,
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
        gpio.write(17, 1)

        # Verify the value was written (StubGPIO.write returns None)
        assert gpio._pins[17].value == 1

    def test_write_nonexistent_pin(self):
        """Test writing to pin that wasn't set up returns silently."""
        gpio = StubGPIO()
        # Should not raise, just does nothing
        gpio.write(99, 1)
        assert 99 not in gpio._pins

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

        # StubGPIO.cleanup() cleans all pins - no single pin cleanup
        gpio.cleanup()

        assert len(gpio._pins) == 0


class TestHardwareAbstractionLayer:
    """Tests for HardwareAbstractionLayer class."""

    def test_init_with_x86_platform(self):
        """Test HAL initialization on x86 platform uses StubGPIO."""
        with patch.object(HardwareAbstractionLayer, "_detect_platform", return_value="x86_64"):
            with patch.object(HardwareAbstractionLayer, "_has_gpio_hardware", return_value=False):
                hal = HardwareAbstractionLayer()
                assert isinstance(hal.gpio, StubGPIO)

    def test_get_status(self):
        """Test getting HAL status."""
        with patch.object(HardwareAbstractionLayer, "_detect_platform", return_value="linux"):
            with patch.object(HardwareAbstractionLayer, "_has_gpio_hardware", return_value=False):
                hal = HardwareAbstractionLayer()
                status = hal.get_status()

                assert "platform" in status
                assert "gpio_available" in status
                assert "i2c_available" in status
                assert "camera_available" in status

    def test_gpio_setup_via_hal(self):
        """Test setting up GPIO pin via HAL."""
        with patch.object(HardwareAbstractionLayer, "_detect_platform", return_value="x86_64"):
            with patch.object(HardwareAbstractionLayer, "_has_gpio_hardware", return_value=False):
                hal = HardwareAbstractionLayer()
                result = hal.gpio.setup(17, GPIOMode.OUTPUT)
                assert result is True

    def test_gpio_write_via_hal(self):
        """Test writing to GPIO pin via HAL."""
        with patch.object(HardwareAbstractionLayer, "_detect_platform", return_value="x86_64"):
            with patch.object(HardwareAbstractionLayer, "_has_gpio_hardware", return_value=False):
                hal = HardwareAbstractionLayer()
                hal.gpio.setup(17, GPIOMode.OUTPUT)
                hal.gpio.write(17, 1)
                # StubGPIO should store the value
                assert hal.gpio._pins[17].value == 1

    def test_gpio_read_via_hal(self):
        """Test reading from GPIO pin via HAL."""
        with patch.object(HardwareAbstractionLayer, "_detect_platform", return_value="x86_64"):
            with patch.object(HardwareAbstractionLayer, "_has_gpio_hardware", return_value=False):
                hal = HardwareAbstractionLayer()
                hal.gpio.setup(27, GPIOMode.INPUT)
                value = hal.gpio.read(27)
                assert isinstance(value, int)

    def test_platform_property(self):
        """Test platform property."""
        with patch.object(HardwareAbstractionLayer, "_detect_platform", return_value="raspberry_pi"):
            with patch("croom.platform.hal.RaspberryPiGPIO"):
                hal = HardwareAbstractionLayer()
                assert hal.platform == "raspberry_pi"


class TestHALCleanup:
    """Tests for HAL cleanup functionality."""

    def test_cleanup_all(self):
        """Test cleaning up all GPIO pins."""
        with patch.object(HardwareAbstractionLayer, "_detect_platform", return_value="x86_64"):
            with patch.object(HardwareAbstractionLayer, "_has_gpio_hardware", return_value=False):
                hal = HardwareAbstractionLayer()
                hal.gpio.setup(17, GPIOMode.OUTPUT)
                hal.gpio.setup(27, GPIOMode.INPUT)

                hal.cleanup()

                # Should not raise and pins should be cleaned
                assert len(hal.gpio._pins) == 0

    def test_hal_properties(self):
        """Test HAL interface properties."""
        with patch.object(HardwareAbstractionLayer, "_detect_platform", return_value="x86_64"):
            with patch.object(HardwareAbstractionLayer, "_has_gpio_hardware", return_value=False):
                hal = HardwareAbstractionLayer()

                assert hal.gpio is not None
                assert hal.i2c is not None
                assert hal.camera is not None
                assert hal.display is not None


class TestGPIOEdge:
    """Tests for GPIOEdge enum."""

    def test_values(self):
        """Test GPIO edge enum values."""
        assert GPIOEdge.RISING.value == "rising"
        assert GPIOEdge.FALLING.value == "falling"
        assert GPIOEdge.BOTH.value == "both"


class TestLinuxGPIO:
    """Tests for LinuxGPIO class."""

    def test_init(self):
        """Test LinuxGPIO initialization."""
        with patch("croom.platform.hal.gpiod", create=True):
            gpio = LinuxGPIO()
            assert gpio is not None

    def test_setup_stores_pin(self):
        """Test setup stores pin configuration."""
        gpio = LinuxGPIO()
        gpio._chip = None  # Force sysfs fallback
        gpio._pins = {}

        # Mock the sysfs paths
        with patch("croom.platform.hal.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.write_text = MagicMock()
            mock_path.__truediv__ = MagicMock(return_value=mock_path)
            mock_path_class.return_value = mock_path

            result = gpio.setup(17, GPIOMode.OUTPUT)
            # Pin should be tracked
            assert 17 in gpio._pins

    def test_read_returns_int(self):
        """Test reading from GPIO pin returns int."""
        gpio = LinuxGPIO()
        gpio._chip = None

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "1"

        with patch("croom.platform.hal.Path", return_value=mock_path):
            value = gpio.read(17)
            assert isinstance(value, int)

    def test_write_no_error(self):
        """Test writing to GPIO pin doesn't raise."""
        gpio = LinuxGPIO()
        gpio._chip = None

        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with patch("croom.platform.hal.Path", return_value=mock_path):
            # Should not raise
            gpio.write(17, 1)


class TestSoftwarePWM:
    """Tests for SoftwarePWM class."""

    def test_init(self):
        """Test SoftwarePWM initialization."""
        mock_gpio = MagicMock()
        pwm = SoftwarePWM(mock_gpio, 17, 1000, 50.0)

        assert pwm._pin == 17
        assert pwm._frequency == 1000
        assert pwm._duty_cycle == 50.0
        assert pwm._running is False

    def test_start(self):
        """Test starting PWM."""
        mock_gpio = MagicMock()
        pwm = SoftwarePWM(mock_gpio, 17, 1000, 50.0)

        pwm.start()
        assert pwm._running is True

        # Clean up
        pwm.stop()

    def test_stop(self):
        """Test stopping PWM."""
        mock_gpio = MagicMock()
        pwm = SoftwarePWM(mock_gpio, 17, 1000, 50.0)

        pwm.start()
        pwm.stop()

        assert pwm._running is False

    def test_change_duty_cycle(self):
        """Test changing duty cycle."""
        mock_gpio = MagicMock()
        pwm = SoftwarePWM(mock_gpio, 17, 1000, 50.0)

        pwm.change_duty_cycle(75)

        assert pwm._duty_cycle == 75

    def test_change_frequency(self):
        """Test changing frequency."""
        mock_gpio = MagicMock()
        pwm = SoftwarePWM(mock_gpio, 17, 1000, 50.0)

        pwm.change_frequency(2000)

        assert pwm._frequency == 2000

    def test_duty_cycle_bounded_max(self):
        """Test duty cycle is bounded at 100."""
        mock_gpio = MagicMock()
        pwm = SoftwarePWM(mock_gpio, 17, 1000, 50.0)

        pwm.change_duty_cycle(150)
        assert pwm._duty_cycle == 100

    def test_duty_cycle_bounded_min(self):
        """Test duty cycle is bounded at 0."""
        mock_gpio = MagicMock()
        pwm = SoftwarePWM(mock_gpio, 17, 1000, 50.0)

        pwm.change_duty_cycle(-10)
        assert pwm._duty_cycle == 0


class TestGPIOEventMonitor:
    """Tests for GPIOEventMonitor class."""

    def test_init(self):
        """Test GPIOEventMonitor initialization."""
        mock_gpio = MagicMock()
        mock_gpio.read.return_value = 0

        monitor = GPIOEventMonitor(mock_gpio)

        assert monitor._gpio == mock_gpio
        assert len(monitor._callbacks) == 0
        assert monitor._running is False

    def test_add_callback(self):
        """Test adding callback."""
        mock_gpio = MagicMock()
        mock_gpio.read.return_value = 0

        monitor = GPIOEventMonitor(mock_gpio)

        callback = MagicMock()
        monitor.add_callback(pin=17, edge=GPIOEdge.RISING, callback=callback, bouncetime=200)

        assert 17 in monitor._callbacks
        assert monitor._callbacks[17][0] == GPIOEdge.RISING
        assert monitor._callbacks[17][1] == callback
        assert monitor._callbacks[17][2] == 200

        # Clean up
        monitor.stop()

    def test_remove_callback(self):
        """Test removing callback."""
        mock_gpio = MagicMock()
        mock_gpio.read.return_value = 0

        monitor = GPIOEventMonitor(mock_gpio)

        callback = MagicMock()
        monitor.add_callback(pin=17, edge=GPIOEdge.RISING, callback=callback, bouncetime=200)
        monitor.remove_callback(17)

        assert 17 not in monitor._callbacks

        # Clean up
        monitor.stop()

    def test_stop_monitoring(self):
        """Test stopping event monitoring."""
        mock_gpio = MagicMock()
        mock_gpio.read.return_value = 0

        monitor = GPIOEventMonitor(mock_gpio)
        monitor._running = True

        monitor.stop()

        assert monitor._running is False
