"""
Hardware Abstraction Layer (HAL) for Croom.

Provides unified interfaces for platform-specific hardware features
including GPIO, I2C, SPI, camera, display, and sensors.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GPIOMode(Enum):
    """GPIO pin modes."""
    INPUT = "input"
    OUTPUT = "output"
    PWM = "pwm"
    ALT0 = "alt0"
    ALT1 = "alt1"


class GPIOPull(Enum):
    """GPIO pull-up/down resistor settings."""
    NONE = "none"
    UP = "up"
    DOWN = "down"


class GPIOEdge(Enum):
    """GPIO edge detection."""
    RISING = "rising"
    FALLING = "falling"
    BOTH = "both"


@dataclass
class GPIOPin:
    """GPIO pin configuration and state."""
    number: int
    mode: GPIOMode = GPIOMode.INPUT
    pull: GPIOPull = GPIOPull.NONE
    value: int = 0
    pwm_frequency: int = 0
    pwm_duty_cycle: float = 0


class GPIOInterface(ABC):
    """Abstract GPIO interface."""

    @abstractmethod
    def setup(self, pin: int, mode: GPIOMode, pull: GPIOPull = GPIOPull.NONE) -> bool:
        """Configure a GPIO pin."""
        pass

    @abstractmethod
    def read(self, pin: int) -> int:
        """Read GPIO pin state."""
        pass

    @abstractmethod
    def write(self, pin: int, value: int) -> None:
        """Write GPIO pin state."""
        pass

    @abstractmethod
    def pwm_start(self, pin: int, frequency: int, duty_cycle: float) -> None:
        """Start PWM on a pin."""
        pass

    @abstractmethod
    def pwm_stop(self, pin: int) -> None:
        """Stop PWM on a pin."""
        pass

    @abstractmethod
    def add_event_detect(
        self,
        pin: int,
        edge: GPIOEdge,
        callback: Callable[[int], None],
        bouncetime: int = 200,
    ) -> None:
        """Add edge detection callback."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Release GPIO resources."""
        pass


class RaspberryPiGPIO(GPIOInterface):
    """GPIO implementation for Raspberry Pi."""

    def __init__(self):
        self._gpio = None
        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
            self._gpio.setmode(GPIO.BCM)
            self._gpio.setwarnings(False)
        except ImportError:
            logger.warning("RPi.GPIO not available")

    def setup(self, pin: int, mode: GPIOMode, pull: GPIOPull = GPIOPull.NONE) -> bool:
        if not self._gpio:
            return False

        gpio_mode = (
            self._gpio.IN if mode == GPIOMode.INPUT else self._gpio.OUT
        )

        pull_map = {
            GPIOPull.NONE: self._gpio.PUD_OFF,
            GPIOPull.UP: self._gpio.PUD_UP,
            GPIOPull.DOWN: self._gpio.PUD_DOWN,
        }

        self._gpio.setup(pin, gpio_mode, pull_up_down=pull_map.get(pull, self._gpio.PUD_OFF))
        return True

    def read(self, pin: int) -> int:
        if not self._gpio:
            return 0
        return self._gpio.input(pin)

    def write(self, pin: int, value: int) -> None:
        if self._gpio:
            self._gpio.output(pin, value)

    def pwm_start(self, pin: int, frequency: int, duty_cycle: float) -> None:
        if not self._gpio:
            return
        # Would need to track PWM objects for proper implementation
        pass

    def pwm_stop(self, pin: int) -> None:
        pass

    def add_event_detect(
        self,
        pin: int,
        edge: GPIOEdge,
        callback: Callable[[int], None],
        bouncetime: int = 200,
    ) -> None:
        if not self._gpio:
            return

        edge_map = {
            GPIOEdge.RISING: self._gpio.RISING,
            GPIOEdge.FALLING: self._gpio.FALLING,
            GPIOEdge.BOTH: self._gpio.BOTH,
        }

        self._gpio.add_event_detect(
            pin,
            edge_map.get(edge, self._gpio.BOTH),
            callback=callback,
            bouncetime=bouncetime,
        )

    def cleanup(self) -> None:
        if self._gpio:
            self._gpio.cleanup()


class StubGPIO(GPIOInterface):
    """
    Stub GPIO implementation for systems without GPIO hardware.

    Used on x86_64 PCs and servers where GPIO is not available.
    All operations succeed but do nothing.
    """

    def __init__(self):
        self._pins: Dict[int, GPIOPin] = {}
        logger.info("Using StubGPIO - no physical GPIO available")

    def setup(self, pin: int, mode: GPIOMode, pull: GPIOPull = GPIOPull.NONE) -> bool:
        """Configure a GPIO pin (no-op)."""
        self._pins[pin] = GPIOPin(number=pin, mode=mode, pull=pull)
        logger.debug(f"StubGPIO: setup pin {pin} as {mode.value}")
        return True

    def read(self, pin: int) -> int:
        """Read GPIO pin state (always returns 0)."""
        return self._pins.get(pin, GPIOPin(number=pin)).value

    def write(self, pin: int, value: int) -> None:
        """Write GPIO pin state (stores in memory only)."""
        if pin in self._pins:
            self._pins[pin].value = value
        logger.debug(f"StubGPIO: write pin {pin} = {value}")

    def pwm_start(self, pin: int, frequency: int, duty_cycle: float) -> None:
        """Start PWM on a pin (no-op)."""
        if pin in self._pins:
            self._pins[pin].pwm_frequency = frequency
            self._pins[pin].pwm_duty_cycle = duty_cycle
        logger.debug(f"StubGPIO: PWM start pin {pin}, freq={frequency}, duty={duty_cycle}")

    def pwm_stop(self, pin: int) -> None:
        """Stop PWM on a pin (no-op)."""
        if pin in self._pins:
            self._pins[pin].pwm_frequency = 0
            self._pins[pin].pwm_duty_cycle = 0

    def add_event_detect(
        self,
        pin: int,
        edge: GPIOEdge,
        callback: Callable[[int], None],
        bouncetime: int = 200,
    ) -> None:
        """Add edge detection callback (no-op)."""
        logger.debug(f"StubGPIO: event detect on pin {pin} (no physical GPIO)")

    def cleanup(self) -> None:
        """Release GPIO resources (no-op)."""
        self._pins.clear()
        logger.debug("StubGPIO: cleanup complete")


class LinuxGPIO(GPIOInterface):
    """GPIO implementation using Linux sysfs or gpiod."""

    def __init__(self):
        self._pins: Dict[int, GPIOPin] = {}
        self._chip = None
        try:
            import gpiod
            self._chip = gpiod.Chip('gpiochip0')
        except (ImportError, Exception):
            logger.warning("gpiod not available, falling back to sysfs")

    def setup(self, pin: int, mode: GPIOMode, pull: GPIOPull = GPIOPull.NONE) -> bool:
        self._pins[pin] = GPIOPin(number=pin, mode=mode, pull=pull)

        if self._chip:
            return True

        # Sysfs fallback
        export_path = Path(f"/sys/class/gpio/export")
        gpio_path = Path(f"/sys/class/gpio/gpio{pin}")

        if not gpio_path.exists():
            try:
                export_path.write_text(str(pin))
            except Exception as e:
                logger.error(f"Failed to export GPIO {pin}: {e}")
                return False

        direction = "in" if mode == GPIOMode.INPUT else "out"
        try:
            (gpio_path / "direction").write_text(direction)
        except Exception as e:
            logger.error(f"Failed to set GPIO {pin} direction: {e}")
            return False

        return True

    def read(self, pin: int) -> int:
        if self._chip:
            try:
                line = self._chip.get_line(pin)
                line.request(consumer="croom", type=1)  # INPUT
                value = line.get_value()
                line.release()
                return value
            except Exception:
                return 0

        gpio_path = Path(f"/sys/class/gpio/gpio{pin}/value")
        if gpio_path.exists():
            try:
                return int(gpio_path.read_text().strip())
            except Exception:
                pass
        return 0

    def write(self, pin: int, value: int) -> None:
        if self._chip:
            try:
                line = self._chip.get_line(pin)
                line.request(consumer="croom", type=2)  # OUTPUT
                line.set_value(value)
                line.release()
                return
            except Exception:
                pass

        gpio_path = Path(f"/sys/class/gpio/gpio{pin}/value")
        if gpio_path.exists():
            try:
                gpio_path.write_text(str(value))
            except Exception as e:
                logger.error(f"Failed to write GPIO {pin}: {e}")

    def pwm_start(self, pin: int, frequency: int, duty_cycle: float) -> None:
        # Software PWM would be needed
        pass

    def pwm_stop(self, pin: int) -> None:
        pass

    def add_event_detect(
        self,
        pin: int,
        edge: GPIOEdge,
        callback: Callable[[int], None],
        bouncetime: int = 200,
    ) -> None:
        # Would need async monitoring implementation
        pass

    def cleanup(self) -> None:
        for pin in self._pins:
            unexport_path = Path("/sys/class/gpio/unexport")
            try:
                unexport_path.write_text(str(pin))
            except Exception:
                pass


class I2CInterface(ABC):
    """Abstract I2C interface."""

    @abstractmethod
    def read_byte(self, address: int, register: int) -> int:
        pass

    @abstractmethod
    def write_byte(self, address: int, register: int, value: int) -> None:
        pass

    @abstractmethod
    def read_block(self, address: int, register: int, length: int) -> bytes:
        pass

    @abstractmethod
    def write_block(self, address: int, register: int, data: bytes) -> None:
        pass

    @abstractmethod
    def scan(self) -> List[int]:
        """Scan for devices on the bus."""
        pass


class LinuxI2C(I2CInterface):
    """I2C implementation using Linux smbus."""

    def __init__(self, bus: int = 1):
        self._bus_num = bus
        self._bus = None
        try:
            import smbus2
            self._bus = smbus2.SMBus(bus)
        except ImportError:
            try:
                import smbus
                self._bus = smbus.SMBus(bus)
            except ImportError:
                logger.warning("smbus not available")

    def read_byte(self, address: int, register: int) -> int:
        if not self._bus:
            return 0
        return self._bus.read_byte_data(address, register)

    def write_byte(self, address: int, register: int, value: int) -> None:
        if self._bus:
            self._bus.write_byte_data(address, register, value)

    def read_block(self, address: int, register: int, length: int) -> bytes:
        if not self._bus:
            return bytes(length)
        return bytes(self._bus.read_i2c_block_data(address, register, length))

    def write_block(self, address: int, register: int, data: bytes) -> None:
        if self._bus:
            self._bus.write_i2c_block_data(address, register, list(data))

    def scan(self) -> List[int]:
        devices = []
        if not self._bus:
            return devices

        for address in range(0x03, 0x78):
            try:
                self._bus.read_byte(address)
                devices.append(address)
            except Exception:
                pass

        return devices


class CameraInterface(ABC):
    """Abstract camera interface."""

    @abstractmethod
    async def open(self, device: str = "/dev/video0") -> bool:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def capture_frame(self) -> Optional[bytes]:
        pass

    @abstractmethod
    async def set_resolution(self, width: int, height: int) -> bool:
        pass

    @abstractmethod
    async def set_framerate(self, fps: int) -> bool:
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        pass


class V4L2Camera(CameraInterface):
    """Camera implementation using V4L2."""

    def __init__(self):
        self._device = None
        self._width = 1920
        self._height = 1080
        self._fps = 30
        self._cap = None

    async def open(self, device: str = "/dev/video0") -> bool:
        try:
            import cv2
            self._cap = cv2.VideoCapture(device)
            if not self._cap.isOpened():
                return False

            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
            self._cap.set(cv2.CAP_PROP_FPS, self._fps)

            self._device = device
            return True

        except ImportError:
            logger.error("OpenCV not available for camera access")
            return False
        except Exception as e:
            logger.error(f"Failed to open camera: {e}")
            return False

    async def close(self) -> None:
        if self._cap:
            self._cap.release()
            self._cap = None

    async def capture_frame(self) -> Optional[bytes]:
        if not self._cap:
            return None

        ret, frame = self._cap.read()
        if ret:
            import cv2
            _, buffer = cv2.imencode('.jpg', frame)
            return buffer.tobytes()
        return None

    async def set_resolution(self, width: int, height: int) -> bool:
        self._width = width
        self._height = height
        if self._cap:
            import cv2
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        return True

    async def set_framerate(self, fps: int) -> bool:
        self._fps = fps
        if self._cap:
            import cv2
            self._cap.set(cv2.CAP_PROP_FPS, fps)
        return True

    def get_capabilities(self) -> Dict[str, Any]:
        caps = {
            "device": self._device,
            "width": self._width,
            "height": self._height,
            "fps": self._fps,
        }

        if self._cap:
            import cv2
            caps["actual_width"] = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            caps["actual_height"] = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            caps["actual_fps"] = int(self._cap.get(cv2.CAP_PROP_FPS))

        return caps


class DisplayInterface(ABC):
    """Abstract display interface."""

    @abstractmethod
    async def get_displays(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def set_brightness(self, brightness: float, display: int = 0) -> bool:
        pass

    @abstractmethod
    async def get_brightness(self, display: int = 0) -> float:
        pass

    @abstractmethod
    async def set_power(self, on: bool, display: int = 0) -> bool:
        pass

    @abstractmethod
    async def is_powered(self, display: int = 0) -> bool:
        pass


class LinuxDisplay(DisplayInterface):
    """Display interface using Linux sysfs and xrandr."""

    def __init__(self):
        self._backlight_path = Path("/sys/class/backlight")

    async def get_displays(self) -> List[Dict[str, Any]]:
        displays = []

        try:
            proc = await asyncio.create_subprocess_exec(
                "xrandr", "--query",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()

            current_display = None
            for line in stdout.decode().split('\n'):
                if " connected" in line:
                    parts = line.split()
                    name = parts[0]
                    current_display = {"name": name, "connected": True}

                    # Parse resolution if present
                    for part in parts:
                        if 'x' in part and '+' in part:
                            res = part.split('+')[0]
                            w, h = res.split('x')
                            current_display["width"] = int(w)
                            current_display["height"] = int(h)
                            break

                    displays.append(current_display)

        except Exception as e:
            logger.error(f"Failed to enumerate displays: {e}")

        return displays

    async def set_brightness(self, brightness: float, display: int = 0) -> bool:
        brightness = max(0, min(1, brightness))

        # Try backlight sysfs
        for backlight in self._backlight_path.iterdir():
            max_file = backlight / "max_brightness"
            cur_file = backlight / "brightness"

            if max_file.exists() and cur_file.exists():
                try:
                    max_brightness = int(max_file.read_text().strip())
                    target = int(brightness * max_brightness)
                    cur_file.write_text(str(target))
                    return True
                except Exception as e:
                    logger.error(f"Failed to set backlight: {e}")

        # Try xrandr
        try:
            displays = await self.get_displays()
            if display < len(displays):
                display_name = displays[display]["name"]
                proc = await asyncio.create_subprocess_exec(
                    "xrandr", "--output", display_name,
                    "--brightness", str(brightness),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.communicate()
                return proc.returncode == 0
        except Exception:
            pass

        return False

    async def get_brightness(self, display: int = 0) -> float:
        for backlight in self._backlight_path.iterdir():
            max_file = backlight / "max_brightness"
            cur_file = backlight / "brightness"

            if max_file.exists() and cur_file.exists():
                try:
                    max_brightness = int(max_file.read_text().strip())
                    cur_brightness = int(cur_file.read_text().strip())
                    return cur_brightness / max_brightness
                except Exception:
                    pass

        return 1.0

    async def set_power(self, on: bool, display: int = 0) -> bool:
        try:
            displays = await self.get_displays()
            if display < len(displays):
                display_name = displays[display]["name"]
                mode = "--auto" if on else "--off"
                proc = await asyncio.create_subprocess_exec(
                    "xrandr", "--output", display_name, mode,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.communicate()
                return proc.returncode == 0
        except Exception:
            pass
        return False

    async def is_powered(self, display: int = 0) -> bool:
        displays = await self.get_displays()
        return display < len(displays)


class HardwareAbstractionLayer:
    """Main HAL providing unified access to hardware features."""

    def __init__(self, platform: str = "auto"):
        """
        Initialize HAL.

        Args:
            platform: Platform type (auto, raspberry_pi, linux, x86_64)
        """
        self._platform = platform if platform != "auto" else self._detect_platform()
        self._arch = self._detect_arch()

        # Initialize interfaces
        self._gpio: Optional[GPIOInterface] = None
        self._i2c: Optional[I2CInterface] = None
        self._camera: Optional[CameraInterface] = None
        self._display: Optional[DisplayInterface] = None

        self._init_interfaces()

    def _detect_platform(self) -> str:
        """Detect current platform."""
        import platform as plat

        # Check for Raspberry Pi
        if Path("/proc/device-tree/model").exists():
            try:
                model = Path("/proc/device-tree/model").read_text()
                if "Raspberry Pi" in model:
                    return "raspberry_pi"
                elif "Jetson" in model:
                    return "jetson"
            except Exception:
                pass

        # Check architecture
        if plat.machine() in ("x86_64", "amd64"):
            return "x86_64"

        return "linux"

    def _detect_arch(self) -> str:
        """Detect CPU architecture."""
        import platform as plat
        return plat.machine()

    def _has_gpio_hardware(self) -> bool:
        """Check if GPIO hardware is available."""
        # GPIO is typically only on SBCs like Raspberry Pi
        if self._platform == "raspberry_pi":
            return True
        if self._platform == "jetson":
            return True
        # x86_64 systems typically don't have GPIO
        if self._arch in ("x86_64", "amd64"):
            return Path("/dev/gpiochip0").exists()
        return Path("/sys/class/gpio").exists()

    def _init_interfaces(self) -> None:
        """Initialize hardware interfaces based on detected platform."""
        # GPIO initialization
        if self._platform == "raspberry_pi":
            self._gpio = RaspberryPiGPIO()
        elif self._has_gpio_hardware():
            self._gpio = LinuxGPIO()
        else:
            # Use stub for x86_64 and systems without GPIO
            self._gpio = StubGPIO()

        # I2C - works on all Linux systems if available
        self._i2c = LinuxI2C()

        # Camera - V4L2 works on all Linux
        self._camera = V4L2Camera()

        # Display
        self._display = LinuxDisplay()

        logger.info(f"HAL initialized: platform={self._platform}, arch={self._arch}")

    @property
    def gpio(self) -> GPIOInterface:
        return self._gpio

    @property
    def i2c(self) -> I2CInterface:
        return self._i2c

    @property
    def camera(self) -> CameraInterface:
        return self._camera

    @property
    def display(self) -> DisplayInterface:
        return self._display

    @property
    def platform(self) -> str:
        return self._platform

    def cleanup(self) -> None:
        """Release all hardware resources."""
        if self._gpio:
            self._gpio.cleanup()

    def get_status(self) -> Dict[str, Any]:
        """Get HAL status."""
        return {
            "platform": self._platform,
            "gpio_available": self._gpio is not None,
            "i2c_available": self._i2c is not None,
            "camera_available": self._camera is not None,
            "display_available": self._display is not None,
        }


# Singleton instance
_hal_instance: Optional[HardwareAbstractionLayer] = None


def get_hal() -> HardwareAbstractionLayer:
    """Get HAL singleton instance."""
    global _hal_instance
    if _hal_instance is None:
        _hal_instance = HardwareAbstractionLayer()
    return _hal_instance
