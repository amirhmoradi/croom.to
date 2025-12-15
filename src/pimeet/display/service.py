"""
Display Service for PiMeet.

High-level display management with HDMI-CEC and DDC/CI control.
Supports both Raspberry Pi (via CEC) and x86_64 systems (via DDC/CI).
"""

import asyncio
import logging
import re
import subprocess
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pimeet.display.cec import (
    CECController,
    CECDevice,
    CECPowerStatus,
)

logger = logging.getLogger(__name__)


class DDCDisplayInfo:
    """Information about a DDC/CI capable display."""

    def __init__(self, display_number: int, bus_number: int, name: str = ""):
        self.display_number = display_number
        self.bus_number = bus_number
        self.name = name
        self.brightness = 50
        self.contrast = 50
        self.power_mode = "on"


class DDCController:
    """
    DDC/CI display controller for x86_64 systems.

    Uses ddcutil to control monitor brightness, power, and other settings.
    Works with external monitors connected via HDMI, DisplayPort, DVI, or VGA.
    """

    # DDC/CI VCP feature codes
    VCP_BRIGHTNESS = 0x10
    VCP_CONTRAST = 0x12
    VCP_POWER_MODE = 0xD6
    VCP_INPUT_SOURCE = 0x60

    # Power modes
    POWER_ON = 0x01
    POWER_STANDBY = 0x02
    POWER_SUSPEND = 0x03
    POWER_OFF = 0x04
    POWER_OFF_HARD = 0x05

    def __init__(self):
        self._available = False
        self._displays: List[DDCDisplayInfo] = []
        self._ddcutil_path: Optional[str] = None

    async def initialize(self) -> bool:
        """
        Initialize DDC/CI controller.

        Returns:
            True if ddcutil is available and monitors are detected.
        """
        # Check if ddcutil is installed
        self._ddcutil_path = await self._find_ddcutil()
        if not self._ddcutil_path:
            logger.warning("ddcutil not found - DDC/CI control unavailable")
            return False

        # Detect monitors
        await self._detect_displays()

        self._available = len(self._displays) > 0
        if self._available:
            logger.info(f"DDC/CI initialized with {len(self._displays)} display(s)")
        else:
            logger.warning("No DDC/CI capable displays found")

        return self._available

    async def _find_ddcutil(self) -> Optional[str]:
        """Find ddcutil executable."""
        paths = ["/usr/bin/ddcutil", "/usr/local/bin/ddcutil"]

        for path in paths:
            if Path(path).exists():
                return path

        # Try which
        try:
            proc = await asyncio.create_subprocess_exec(
                "which", "ddcutil",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode().strip()
        except Exception:
            pass

        return None

    async def _detect_displays(self) -> None:
        """Detect DDC/CI capable displays."""
        self._displays.clear()

        if not self._ddcutil_path:
            return

        try:
            proc = await asyncio.create_subprocess_exec(
                self._ddcutil_path, "detect", "--brief",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)

            if proc.returncode != 0:
                return

            output = stdout.decode()

            # Parse output: "Display 1\n   I2C bus:  /dev/i2c-1\n   Monitor:   Dell..."
            display_num = 0
            bus_num = 0
            name = ""

            for line in output.split('\n'):
                if line.startswith("Display"):
                    if display_num > 0 and bus_num > 0:
                        self._displays.append(DDCDisplayInfo(display_num, bus_num, name))

                    match = re.search(r'Display\s+(\d+)', line)
                    if match:
                        display_num = int(match.group(1))
                    bus_num = 0
                    name = ""

                elif "I2C bus:" in line:
                    match = re.search(r'/dev/i2c-(\d+)', line)
                    if match:
                        bus_num = int(match.group(1))

                elif "Monitor:" in line:
                    name = line.split(":", 1)[-1].strip()

            # Add last display
            if display_num > 0 and bus_num > 0:
                self._displays.append(DDCDisplayInfo(display_num, bus_num, name))

        except asyncio.TimeoutError:
            logger.warning("DDC detect timed out")
        except Exception as e:
            logger.error(f"DDC detect error: {e}")

    async def _run_ddcutil(self, *args, timeout: float = 10.0) -> Optional[str]:
        """Run ddcutil command."""
        if not self._ddcutil_path:
            return None

        try:
            proc = await asyncio.create_subprocess_exec(
                self._ddcutil_path, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            if proc.returncode == 0:
                return stdout.decode()
            else:
                logger.debug(f"ddcutil error: {stderr.decode()}")
                return None

        except asyncio.TimeoutError:
            logger.warning(f"ddcutil command timed out: {args}")
            return None
        except Exception as e:
            logger.error(f"ddcutil error: {e}")
            return None

    async def get_brightness(self, display: int = 1) -> int:
        """
        Get display brightness level.

        Args:
            display: Display number (1-based)

        Returns:
            Brightness level (0-100)
        """
        output = await self._run_ddcutil(
            "getvcp", hex(self.VCP_BRIGHTNESS),
            "--display", str(display),
        )

        if output:
            # Parse "VCP code 0x10 (Brightness): current value = 50, max value = 100"
            match = re.search(r'current value\s*=\s*(\d+)', output)
            if match:
                return int(match.group(1))

        return 50  # Default

    async def set_brightness(self, level: int, display: int = 1) -> bool:
        """
        Set display brightness level.

        Args:
            level: Brightness level (0-100)
            display: Display number (1-based)

        Returns:
            True if successful
        """
        level = max(0, min(100, level))

        result = await self._run_ddcutil(
            "setvcp", hex(self.VCP_BRIGHTNESS), str(level),
            "--display", str(display),
        )

        success = result is not None
        if success:
            logger.debug(f"Set display {display} brightness to {level}")
        return success

    async def get_contrast(self, display: int = 1) -> int:
        """Get display contrast level."""
        output = await self._run_ddcutil(
            "getvcp", hex(self.VCP_CONTRAST),
            "--display", str(display),
        )

        if output:
            match = re.search(r'current value\s*=\s*(\d+)', output)
            if match:
                return int(match.group(1))

        return 50

    async def set_contrast(self, level: int, display: int = 1) -> bool:
        """Set display contrast level."""
        level = max(0, min(100, level))

        result = await self._run_ddcutil(
            "setvcp", hex(self.VCP_CONTRAST), str(level),
            "--display", str(display),
        )

        return result is not None

    async def power_on(self, display: int = 1) -> bool:
        """
        Power on a display.

        Args:
            display: Display number (1-based)

        Returns:
            True if successful
        """
        result = await self._run_ddcutil(
            "setvcp", hex(self.VCP_POWER_MODE), str(self.POWER_ON),
            "--display", str(display),
        )

        success = result is not None
        if success:
            logger.info(f"Powered on display {display} via DDC/CI")
        return success

    async def power_off(self, display: int = 1) -> bool:
        """
        Put display in standby mode.

        Args:
            display: Display number (1-based)

        Returns:
            True if successful
        """
        # Try standby first (soft off)
        result = await self._run_ddcutil(
            "setvcp", hex(self.VCP_POWER_MODE), str(self.POWER_STANDBY),
            "--display", str(display),
        )

        success = result is not None
        if success:
            logger.info(f"Put display {display} in standby via DDC/CI")
        return success

    async def get_power_status(self, display: int = 1) -> str:
        """
        Get display power status.

        Returns:
            'on', 'standby', 'suspend', 'off', or 'unknown'
        """
        output = await self._run_ddcutil(
            "getvcp", hex(self.VCP_POWER_MODE),
            "--display", str(display),
        )

        if output:
            match = re.search(r'current value\s*=\s*(\d+)', output)
            if match:
                value = int(match.group(1))
                if value == self.POWER_ON:
                    return "on"
                elif value == self.POWER_STANDBY:
                    return "standby"
                elif value == self.POWER_SUSPEND:
                    return "suspend"
                elif value in (self.POWER_OFF, self.POWER_OFF_HARD):
                    return "off"

        return "unknown"

    async def set_input_source(self, source: int, display: int = 1) -> bool:
        """
        Set display input source.

        Common source values:
        - 0x01: VGA-1
        - 0x03: DVI-1
        - 0x04: DVI-2
        - 0x0F: DisplayPort-1
        - 0x10: DisplayPort-2
        - 0x11: HDMI-1
        - 0x12: HDMI-2

        Args:
            source: Input source VCP value
            display: Display number

        Returns:
            True if successful
        """
        result = await self._run_ddcutil(
            "setvcp", hex(self.VCP_INPUT_SOURCE), str(source),
            "--display", str(display),
        )

        return result is not None

    @property
    def is_available(self) -> bool:
        """Check if DDC/CI is available."""
        return self._available

    @property
    def displays(self) -> List[DDCDisplayInfo]:
        """Get list of detected displays."""
        return self._displays.copy()

    @property
    def display_count(self) -> int:
        """Get number of detected displays."""
        return len(self._displays)


class DisplayState(Enum):
    """Display state."""
    UNKNOWN = "unknown"
    ON = "on"
    OFF = "off"
    STANDBY = "standby"


@dataclass
class DisplayInfo:
    """Information about a connected display."""
    name: str
    resolution: Tuple[int, int]
    refresh_rate: float
    is_connected: bool
    is_primary: bool
    hdmi_port: int


class DisplayService:
    """
    High-level display service for PiMeet.

    Manages displays and provides HDMI-CEC and DDC/CI control.
    Automatically selects the best available control method:
    - CEC for Raspberry Pi and HDMI-connected TVs
    - DDC/CI for x86_64 systems with external monitors
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize display service.

        Args:
            config: Service configuration with:
                - cec_enabled: Enable HDMI-CEC (default True)
                - cec_device: CEC device path (default /dev/cec0)
                - ddc_enabled: Enable DDC/CI (default True)
                - auto_power_on: Power on display when meeting starts
                - auto_power_off: Power off display after inactivity
                - power_off_timeout: Seconds of inactivity before power off
                - wake_on_motion: Wake display on motion detection
        """
        self.config = config or {}

        # CEC controller (for Raspberry Pi / TVs)
        self._cec: Optional[CECController] = None
        self._cec_enabled = self.config.get('cec_enabled', True)

        # DDC/CI controller (for x86_64 / monitors)
        self._ddc: Optional[DDCController] = None
        self._ddc_enabled = self.config.get('ddc_enabled', True)

        # Control method: 'cec', 'ddc', or None
        self._control_method: Optional[str] = None

        # State
        self._display_state = DisplayState.UNKNOWN
        self._displays: List[DisplayInfo] = []

        # Auto power settings
        self._auto_power_on = self.config.get('auto_power_on', True)
        self._auto_power_off = self.config.get('auto_power_off', False)
        self._power_off_timeout = self.config.get('power_off_timeout', 300)  # 5 minutes

        # Activity tracking
        self._last_activity: float = 0
        self._inactivity_task: Optional[asyncio.Task] = None
        self._running = False

        # Callbacks
        self._on_display_change: List[Callable[[DisplayState], None]] = []

    async def initialize(self) -> bool:
        """
        Initialize the display service.

        Tries CEC first (for Raspberry Pi/TVs), then falls back to DDC/CI
        (for x86_64 systems with external monitors).

        Returns:
            True if initialization successful
        """
        try:
            # Initialize CEC if enabled (preferred for Raspberry Pi)
            if self._cec_enabled:
                cec_device = self.config.get('cec_device', '/dev/cec0')
                self._cec = CECController(device=cec_device)

                if await self._cec.initialize():
                    self._control_method = 'cec'
                    logger.info("CEC control enabled")

                    # Get current TV state
                    power = await self._cec.get_tv_power_status()
                    if power == CECPowerStatus.ON:
                        self._display_state = DisplayState.ON
                    elif power == CECPowerStatus.STANDBY:
                        self._display_state = DisplayState.STANDBY
                else:
                    logger.debug("CEC not available, will try DDC/CI")
                    self._cec = None

            # Initialize DDC/CI if CEC not available (for x86_64 systems)
            if not self._cec and self._ddc_enabled:
                self._ddc = DDCController()

                if await self._ddc.initialize():
                    self._control_method = 'ddc'
                    logger.info("DDC/CI control enabled")

                    # Get current power state
                    power_status = await self._ddc.get_power_status()
                    if power_status == "on":
                        self._display_state = DisplayState.ON
                    elif power_status in ("standby", "suspend"):
                        self._display_state = DisplayState.STANDBY
                    elif power_status == "off":
                        self._display_state = DisplayState.OFF
                else:
                    logger.warning("DDC/CI not available")
                    self._ddc = None

            # Detect connected displays
            await self._detect_displays()

            if self._control_method:
                logger.info(f"Display service initialized (control: {self._control_method})")
            else:
                logger.warning("Display service initialized (no power control available)")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize display service: {e}")
            return False

    async def _detect_displays(self) -> None:
        """Detect connected displays using various methods."""
        self._displays.clear()

        # Try xrandr first (X11)
        displays = await self._detect_xrandr()
        if displays:
            self._displays = displays
            return

        # Try wlr-randr (Wayland)
        displays = await self._detect_wlr_randr()
        if displays:
            self._displays = displays
            return

        # Try tvservice (Raspberry Pi)
        displays = await self._detect_tvservice()
        if displays:
            self._displays = displays
            return

        # Try KMS/DRM
        displays = await self._detect_kms()
        if displays:
            self._displays = displays

    async def _run_command(self, *args) -> Optional[str]:
        """Run command and return output."""
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=5.0,
            )
            if process.returncode == 0:
                return stdout.decode()
        except Exception:
            pass
        return None

    async def _detect_xrandr(self) -> List[DisplayInfo]:
        """Detect displays using xrandr."""
        output = await self._run_command("xrandr", "--query")
        if not output:
            return []

        displays = []
        current_display = None

        for line in output.split('\n'):
            # Connected display: "HDMI-1 connected primary 1920x1080+0+0"
            if ' connected' in line:
                parts = line.split()
                name = parts[0]
                is_primary = 'primary' in line

                # Parse resolution
                resolution = (0, 0)
                for part in parts:
                    if 'x' in part and '+' in part:
                        res = part.split('+')[0]
                        w, h = res.split('x')
                        resolution = (int(w), int(h))
                        break

                current_display = DisplayInfo(
                    name=name,
                    resolution=resolution,
                    refresh_rate=60.0,
                    is_connected=True,
                    is_primary=is_primary,
                    hdmi_port=1 if 'HDMI' in name else 0,
                )
                displays.append(current_display)

            # Refresh rate line: "   1920x1080     60.00*+"
            elif current_display and '*' in line:
                parts = line.split()
                for part in parts:
                    if part.endswith('*') or part.endswith('+'):
                        try:
                            rate = float(part.rstrip('*+'))
                            current_display.refresh_rate = rate
                        except ValueError:
                            pass

        return displays

    async def _detect_wlr_randr(self) -> List[DisplayInfo]:
        """Detect displays using wlr-randr (Wayland)."""
        output = await self._run_command("wlr-randr")
        if not output:
            return []

        displays = []
        current_display = None

        for line in output.split('\n'):
            line = line.strip()

            # Display name
            if not line.startswith(' ') and line:
                name = line.split()[0]
                current_display = DisplayInfo(
                    name=name,
                    resolution=(0, 0),
                    refresh_rate=60.0,
                    is_connected=True,
                    is_primary=len(displays) == 0,
                    hdmi_port=1 if 'HDMI' in name else 0,
                )
                displays.append(current_display)

            # Current mode
            elif current_display and 'current' in line.lower():
                # Parse "1920x1080 @ 60.000000 Hz"
                parts = line.split()
                if len(parts) >= 1 and 'x' in parts[0]:
                    w, h = parts[0].split('x')
                    current_display.resolution = (int(w), int(h))
                if '@' in line:
                    idx = parts.index('@')
                    if idx + 1 < len(parts):
                        try:
                            current_display.refresh_rate = float(parts[idx + 1])
                        except ValueError:
                            pass

        return displays

    async def _detect_tvservice(self) -> List[DisplayInfo]:
        """Detect displays using tvservice (Raspberry Pi)."""
        output = await self._run_command("tvservice", "-s")
        if not output:
            return []

        displays = []

        # Parse "state 0x120006 [HDMI CEA (16) RGB lim 16:9], 1920x1080 @ 60.00Hz"
        if 'HDMI' in output and 'x' in output:
            # Extract resolution
            import re
            match = re.search(r'(\d+)x(\d+)', output)
            if match:
                w, h = int(match.group(1)), int(match.group(2))

                # Extract refresh rate
                rate_match = re.search(r'@\s*([\d.]+)\s*Hz', output)
                rate = float(rate_match.group(1)) if rate_match else 60.0

                displays.append(DisplayInfo(
                    name="HDMI",
                    resolution=(w, h),
                    refresh_rate=rate,
                    is_connected=True,
                    is_primary=True,
                    hdmi_port=1,
                ))

        return displays

    async def _detect_kms(self) -> List[DisplayInfo]:
        """Detect displays using KMS/DRM."""
        from pathlib import Path

        displays = []

        try:
            drm_path = Path('/sys/class/drm')
            if not drm_path.exists():
                return []

            for card in drm_path.glob('card*-*'):
                status_file = card / 'status'
                if status_file.exists():
                    status = status_file.read_text().strip()
                    if status == 'connected':
                        name = card.name

                        # Get modes
                        modes_file = card / 'modes'
                        resolution = (1920, 1080)
                        if modes_file.exists():
                            modes = modes_file.read_text().strip().split('\n')
                            if modes and modes[0]:
                                w, h = modes[0].split('x')
                                resolution = (int(w), int(h))

                        displays.append(DisplayInfo(
                            name=name,
                            resolution=resolution,
                            refresh_rate=60.0,
                            is_connected=True,
                            is_primary=len(displays) == 0,
                            hdmi_port=1 if 'HDMI' in name else 0,
                        ))

        except Exception as e:
            logger.debug(f"KMS detection error: {e}")

        return displays

    async def start(self) -> None:
        """Start the display service."""
        if self._running:
            return

        self._running = True
        self._last_activity = asyncio.get_event_loop().time()

        # Start inactivity monitor if auto power off is enabled
        if self._auto_power_off:
            self._inactivity_task = asyncio.create_task(self._inactivity_monitor())

        logger.info("Display service started")

    async def stop(self) -> None:
        """Stop the display service."""
        if not self._running:
            return

        self._running = False

        if self._inactivity_task:
            self._inactivity_task.cancel()
            try:
                await self._inactivity_task
            except asyncio.CancelledError:
                pass
            self._inactivity_task = None

        logger.info("Display service stopped")

    async def _inactivity_monitor(self) -> None:
        """Monitor for inactivity and power off display."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute

                if not self._auto_power_off:
                    continue

                now = asyncio.get_event_loop().time()
                inactive_seconds = now - self._last_activity

                if inactive_seconds >= self._power_off_timeout:
                    if self._display_state == DisplayState.ON:
                        logger.info("Powering off display due to inactivity")
                        await self.power_off()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Inactivity monitor error: {e}")

    def report_activity(self) -> None:
        """Report user activity to reset inactivity timer."""
        self._last_activity = asyncio.get_event_loop().time()

    async def power_on(self) -> bool:
        """
        Power on the display.

        Uses CEC for TVs or DDC/CI for monitors.

        Returns:
            True if successful
        """
        success = False

        if self._control_method == 'cec' and self._cec:
            success = await self._cec.power_on_tv()

            if success:
                # Set as active source
                await asyncio.sleep(2)  # Wait for TV to wake
                await self._cec.set_active_source()

        elif self._control_method == 'ddc' and self._ddc:
            success = await self._ddc.power_on()

        else:
            logger.warning("No display power control available")
            return False

        if success:
            self._display_state = DisplayState.ON
            self._notify_state_change()
            logger.info(f"Display powered on via {self._control_method}")

        return success

    async def power_off(self) -> bool:
        """
        Put the display in standby.

        Uses CEC for TVs or DDC/CI for monitors.

        Returns:
            True if successful
        """
        success = False

        if self._control_method == 'cec' and self._cec:
            success = await self._cec.power_off_tv()

        elif self._control_method == 'ddc' and self._ddc:
            success = await self._ddc.power_off()

        else:
            logger.warning("No display power control available")
            return False

        if success:
            self._display_state = DisplayState.STANDBY
            self._notify_state_change()
            logger.info(f"Display powered off via {self._control_method}")

        return success

    async def toggle_power(self) -> bool:
        """
        Toggle display power state.

        Returns:
            True if command successful
        """
        if self._display_state == DisplayState.ON:
            return await self.power_off()
        else:
            return await self.power_on()

    async def get_power_status(self) -> DisplayState:
        """
        Get current display power status.

        Returns:
            Current power state
        """
        if self._control_method == 'cec' and self._cec:
            power = await self._cec.get_tv_power_status()

            if power == CECPowerStatus.ON:
                self._display_state = DisplayState.ON
            elif power == CECPowerStatus.STANDBY:
                self._display_state = DisplayState.STANDBY
            elif power in (CECPowerStatus.IN_TRANSITION_ON, CECPowerStatus.IN_TRANSITION_STANDBY):
                # Keep current state during transition
                pass
            else:
                self._display_state = DisplayState.UNKNOWN

        elif self._control_method == 'ddc' and self._ddc:
            power_status = await self._ddc.get_power_status()

            if power_status == "on":
                self._display_state = DisplayState.ON
            elif power_status in ("standby", "suspend"):
                self._display_state = DisplayState.STANDBY
            elif power_status == "off":
                self._display_state = DisplayState.OFF
            else:
                self._display_state = DisplayState.UNKNOWN
        else:
            self._display_state = DisplayState.UNKNOWN

        return self._display_state

    async def get_brightness(self) -> int:
        """
        Get display brightness level.

        Returns:
            Brightness level (0-100), or -1 if not supported
        """
        if self._control_method == 'ddc' and self._ddc:
            return await self._ddc.get_brightness()
        return -1

    async def set_brightness(self, level: int) -> bool:
        """
        Set display brightness level.

        Args:
            level: Brightness level (0-100)

        Returns:
            True if successful
        """
        if self._control_method == 'ddc' and self._ddc:
            return await self._ddc.set_brightness(level)
        logger.warning("Brightness control only available via DDC/CI")
        return False

    async def set_active_source(self) -> bool:
        """
        Set this device as the active HDMI source.

        Returns:
            True if successful
        """
        if not self._cec or not self._cec.is_available:
            return False

        return await self._cec.set_active_source()

    async def volume_up(self) -> bool:
        """Send volume up command."""
        if not self._cec or not self._cec.is_available:
            return False
        return await self._cec.volume_up()

    async def volume_down(self) -> bool:
        """Send volume down command."""
        if not self._cec or not self._cec.is_available:
            return False
        return await self._cec.volume_down()

    async def mute(self) -> bool:
        """Send mute toggle command."""
        if not self._cec or not self._cec.is_available:
            return False
        return await self._cec.mute()

    @property
    def displays(self) -> List[DisplayInfo]:
        """Get list of connected displays."""
        return self._displays.copy()

    @property
    def primary_display(self) -> Optional[DisplayInfo]:
        """Get the primary display."""
        return next((d for d in self._displays if d.is_primary), None)

    @property
    def state(self) -> DisplayState:
        """Get current display state."""
        return self._display_state

    @property
    def cec_available(self) -> bool:
        """Whether CEC control is available."""
        return self._cec is not None and self._cec.is_available

    @property
    def ddc_available(self) -> bool:
        """Whether DDC/CI control is available."""
        return self._ddc is not None and self._ddc.is_available

    @property
    def control_method(self) -> Optional[str]:
        """Get the active display control method ('cec', 'ddc', or None)."""
        return self._control_method

    @property
    def has_power_control(self) -> bool:
        """Check if any power control method is available."""
        return self._control_method is not None

    @property
    def has_brightness_control(self) -> bool:
        """Check if brightness control is available (DDC/CI only)."""
        return self._control_method == 'ddc' and self._ddc is not None

    @property
    def cec_devices(self) -> List[CECDevice]:
        """Get list of CEC devices."""
        if self._cec:
            return self._cec.devices
        return []

    @property
    def ddc_displays(self) -> List[DDCDisplayInfo]:
        """Get list of DDC/CI displays."""
        if self._ddc:
            return self._ddc.displays
        return []

    def on_display_change(self, callback: Callable[[DisplayState], None]) -> None:
        """Register callback for display state changes."""
        self._on_display_change.append(callback)

    def _notify_state_change(self) -> None:
        """Notify listeners of state change."""
        for callback in self._on_display_change:
            try:
                callback(self._display_state)
            except Exception as e:
                logger.error(f"Display callback error: {e}")

    async def on_meeting_start(self) -> None:
        """Called when a meeting starts."""
        self.report_activity()

        if self._auto_power_on and self._display_state != DisplayState.ON:
            await self.power_on()

    async def on_meeting_end(self) -> None:
        """Called when a meeting ends."""
        # Activity will naturally decay after meeting
        pass

    async def on_motion_detected(self) -> None:
        """Called when motion is detected (from AI)."""
        self.report_activity()

        if self.config.get('wake_on_motion', True):
            if self._display_state == DisplayState.STANDBY:
                await self.power_on()

    async def shutdown(self) -> None:
        """Shutdown the display service."""
        await self.stop()
        self._cec = None
        self._ddc = None
        self._control_method = None
        self._displays.clear()
        self._on_display_change.clear()
        logger.info("Display service shutdown")


def create_display_service(config: Dict[str, Any]) -> DisplayService:
    """
    Create a display service from configuration.

    Args:
        config: Display configuration dict

    Returns:
        Configured DisplayService instance
    """
    return DisplayService(config)
