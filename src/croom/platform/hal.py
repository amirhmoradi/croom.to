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
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

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
        self._pwm_instances: Dict[int, Any] = {}  # Track PWM instances per pin
        self._event_callbacks: Dict[int, Callable[[int], None]] = {}
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
        """
        Start PWM on a GPIO pin.

        Args:
            pin: BCM GPIO pin number
            frequency: PWM frequency in Hz
            duty_cycle: Duty cycle 0.0-100.0
        """
        if not self._gpio:
            return

        try:
            # Stop existing PWM on this pin if any
            if pin in self._pwm_instances:
                self._pwm_instances[pin].stop()

            # Setup pin as output if not already
            self._gpio.setup(pin, self._gpio.OUT)

            # Create and start PWM
            pwm = self._gpio.PWM(pin, frequency)
            pwm.start(duty_cycle)
            self._pwm_instances[pin] = pwm

            logger.debug(f"Started PWM on pin {pin}: freq={frequency}Hz, duty={duty_cycle}%")
        except Exception as e:
            logger.error(f"Failed to start PWM on pin {pin}: {e}")

    def pwm_stop(self, pin: int) -> None:
        """Stop PWM on a GPIO pin."""
        if pin in self._pwm_instances:
            try:
                self._pwm_instances[pin].stop()
                del self._pwm_instances[pin]
                logger.debug(f"Stopped PWM on pin {pin}")
            except Exception as e:
                logger.error(f"Failed to stop PWM on pin {pin}: {e}")

    def pwm_change_frequency(self, pin: int, frequency: int) -> None:
        """Change PWM frequency on a pin."""
        if pin in self._pwm_instances:
            try:
                self._pwm_instances[pin].ChangeFrequency(frequency)
            except Exception as e:
                logger.error(f"Failed to change PWM frequency on pin {pin}: {e}")

    def pwm_change_duty_cycle(self, pin: int, duty_cycle: float) -> None:
        """Change PWM duty cycle on a pin."""
        if pin in self._pwm_instances:
            try:
                self._pwm_instances[pin].ChangeDutyCycle(duty_cycle)
            except Exception as e:
                logger.error(f"Failed to change PWM duty cycle on pin {pin}: {e}")

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
        """Release all GPIO resources including PWM instances."""
        # Stop all PWM instances
        for pin in list(self._pwm_instances.keys()):
            self.pwm_stop(pin)

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


class SoftwarePWM:
    """Software PWM implementation using threading."""

    def __init__(self, gpio_interface: 'LinuxGPIO', pin: int, frequency: int, duty_cycle: float):
        self._gpio = gpio_interface
        self._pin = pin
        self._frequency = frequency
        self._duty_cycle = duty_cycle
        self._running = False
        self._thread: Optional[Any] = None

    def start(self) -> None:
        """Start software PWM."""
        import threading

        self._running = True
        self._thread = threading.Thread(target=self._pwm_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop software PWM."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def change_frequency(self, frequency: int) -> None:
        """Change PWM frequency."""
        self._frequency = max(1, frequency)

    def change_duty_cycle(self, duty_cycle: float) -> None:
        """Change duty cycle (0-100)."""
        self._duty_cycle = max(0, min(100, duty_cycle))

    def _pwm_loop(self) -> None:
        """Main PWM loop."""
        import time

        while self._running:
            if self._frequency <= 0:
                time.sleep(0.1)
                continue

            period = 1.0 / self._frequency
            on_time = period * (self._duty_cycle / 100.0)
            off_time = period - on_time

            if on_time > 0:
                self._gpio.write(self._pin, 1)
                time.sleep(on_time)

            if off_time > 0 and self._running:
                self._gpio.write(self._pin, 0)
                time.sleep(off_time)


class GPIOEventMonitor:
    """Async GPIO event monitoring using polling or inotify."""

    def __init__(self, gpio_interface: 'LinuxGPIO'):
        self._gpio = gpio_interface
        self._callbacks: Dict[int, Tuple[GPIOEdge, Callable[[int], None], int]] = {}
        self._running = False
        self._thread: Optional[Any] = None
        self._last_values: Dict[int, int] = {}

    def add_callback(
        self,
        pin: int,
        edge: GPIOEdge,
        callback: Callable[[int], None],
        bouncetime: int,
    ) -> None:
        """Add a callback for edge detection."""
        self._callbacks[pin] = (edge, callback, bouncetime)
        self._last_values[pin] = self._gpio.read(pin)

        if not self._running:
            self._start()

    def remove_callback(self, pin: int) -> None:
        """Remove callback for a pin."""
        if pin in self._callbacks:
            del self._callbacks[pin]
        if pin in self._last_values:
            del self._last_values[pin]

    def _start(self) -> None:
        """Start the monitoring thread."""
        import threading

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        import time

        last_trigger: Dict[int, float] = {}

        while self._running:
            for pin, (edge, callback, bouncetime) in list(self._callbacks.items()):
                try:
                    current_value = self._gpio.read(pin)
                    last_value = self._last_values.get(pin, current_value)

                    # Check for edge
                    triggered = False
                    if edge == GPIOEdge.RISING and last_value == 0 and current_value == 1:
                        triggered = True
                    elif edge == GPIOEdge.FALLING and last_value == 1 and current_value == 0:
                        triggered = True
                    elif edge == GPIOEdge.BOTH and last_value != current_value:
                        triggered = True

                    if triggered:
                        # Check bounce time
                        now = time.time()
                        last = last_trigger.get(pin, 0)
                        if (now - last) * 1000 >= bouncetime:
                            last_trigger[pin] = now
                            try:
                                callback(pin)
                            except Exception as e:
                                logger.error(f"GPIO callback error for pin {pin}: {e}")

                    self._last_values[pin] = current_value

                except Exception as e:
                    logger.error(f"Error monitoring pin {pin}: {e}")

            time.sleep(0.01)  # 10ms polling interval


class LinuxGPIO(GPIOInterface):
    """GPIO implementation using Linux sysfs or gpiod."""

    def __init__(self):
        self._pins: Dict[int, GPIOPin] = {}
        self._chip = None
        self._pwm_instances: Dict[int, SoftwarePWM] = {}
        self._event_monitor: Optional[GPIOEventMonitor] = None
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
        """
        Start software PWM on a GPIO pin.

        Args:
            pin: GPIO pin number
            frequency: PWM frequency in Hz
            duty_cycle: Duty cycle 0.0-100.0
        """
        try:
            # Stop existing PWM on this pin if any
            if pin in self._pwm_instances:
                self._pwm_instances[pin].stop()

            # Setup pin as output
            self.setup(pin, GPIOMode.OUTPUT)

            # Create and start software PWM
            pwm = SoftwarePWM(self, pin, frequency, duty_cycle)
            pwm.start()
            self._pwm_instances[pin] = pwm

            logger.debug(f"Started software PWM on pin {pin}: freq={frequency}Hz, duty={duty_cycle}%")
        except Exception as e:
            logger.error(f"Failed to start software PWM on pin {pin}: {e}")

    def pwm_stop(self, pin: int) -> None:
        """Stop software PWM on a GPIO pin."""
        if pin in self._pwm_instances:
            try:
                self._pwm_instances[pin].stop()
                del self._pwm_instances[pin]
                self.write(pin, 0)  # Ensure pin is low
                logger.debug(f"Stopped software PWM on pin {pin}")
            except Exception as e:
                logger.error(f"Failed to stop software PWM on pin {pin}: {e}")

    def pwm_change_frequency(self, pin: int, frequency: int) -> None:
        """Change PWM frequency on a pin."""
        if pin in self._pwm_instances:
            self._pwm_instances[pin].change_frequency(frequency)

    def pwm_change_duty_cycle(self, pin: int, duty_cycle: float) -> None:
        """Change PWM duty cycle on a pin."""
        if pin in self._pwm_instances:
            self._pwm_instances[pin].change_duty_cycle(duty_cycle)

    def add_event_detect(
        self,
        pin: int,
        edge: GPIOEdge,
        callback: Callable[[int], None],
        bouncetime: int = 200,
    ) -> None:
        """
        Add edge detection callback for a GPIO pin.

        Args:
            pin: GPIO pin number
            edge: Edge type to detect (RISING, FALLING, BOTH)
            callback: Function to call when edge is detected
            bouncetime: Minimum time between callbacks in milliseconds
        """
        try:
            # Setup pin as input if not already
            if pin not in self._pins or self._pins[pin].mode != GPIOMode.INPUT:
                self.setup(pin, GPIOMode.INPUT)

            # Create event monitor if needed
            if self._event_monitor is None:
                self._event_monitor = GPIOEventMonitor(self)

            self._event_monitor.add_callback(pin, edge, callback, bouncetime)
            logger.debug(f"Added event detection on pin {pin} for {edge.value} edge")
        except Exception as e:
            logger.error(f"Failed to add event detection on pin {pin}: {e}")

    def remove_event_detect(self, pin: int) -> None:
        """Remove edge detection callback for a GPIO pin."""
        if self._event_monitor:
            self._event_monitor.remove_callback(pin)

    def cleanup(self) -> None:
        """Release all GPIO resources."""
        # Stop all PWM instances
        for pin in list(self._pwm_instances.keys()):
            self.pwm_stop(pin)

        # Stop event monitor
        if self._event_monitor:
            self._event_monitor.stop()
            self._event_monitor = None

        # Unexport GPIO pins
        for pin in self._pins:
            unexport_path = Path("/sys/class/gpio/unexport")
            try:
                unexport_path.write_text(str(pin))
            except Exception:
                pass

        self._pins.clear()


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
