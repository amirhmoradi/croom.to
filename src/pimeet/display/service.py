"""
Display Service for PiMeet.

High-level display management with HDMI-CEC control.
"""

import asyncio
import logging
import subprocess
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

from pimeet.display.cec import (
    CECController,
    CECDevice,
    CECPowerStatus,
)

logger = logging.getLogger(__name__)


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

    Manages displays and provides HDMI-CEC control.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize display service.

        Args:
            config: Service configuration with:
                - cec_enabled: Enable HDMI-CEC (default True)
                - cec_device: CEC device path (default /dev/cec0)
                - auto_power_on: Power on display when meeting starts
                - auto_power_off: Power off display after inactivity
                - power_off_timeout: Seconds of inactivity before power off
                - wake_on_motion: Wake display on motion detection
        """
        self.config = config or {}

        # CEC controller
        self._cec: Optional[CECController] = None
        self._cec_enabled = self.config.get('cec_enabled', True)

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

        Returns:
            True if initialization successful
        """
        try:
            # Initialize CEC if enabled
            if self._cec_enabled:
                cec_device = self.config.get('cec_device', '/dev/cec0')
                self._cec = CECController(device=cec_device)

                if await self._cec.initialize():
                    logger.info("CEC control enabled")

                    # Get current TV state
                    power = await self._cec.get_tv_power_status()
                    if power == CECPowerStatus.ON:
                        self._display_state = DisplayState.ON
                    elif power == CECPowerStatus.STANDBY:
                        self._display_state = DisplayState.STANDBY
                else:
                    logger.warning("CEC not available")
                    self._cec = None

            # Detect connected displays
            await self._detect_displays()

            logger.info("Display service initialized")
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

        Returns:
            True if successful
        """
        if not self._cec or not self._cec.is_available:
            logger.warning("CEC not available for power control")
            return False

        success = await self._cec.power_on_tv()

        if success:
            self._display_state = DisplayState.ON
            self._notify_state_change()

            # Set as active source
            await asyncio.sleep(2)  # Wait for TV to wake
            await self._cec.set_active_source()

        return success

    async def power_off(self) -> bool:
        """
        Put the display in standby.

        Returns:
            True if successful
        """
        if not self._cec or not self._cec.is_available:
            logger.warning("CEC not available for power control")
            return False

        success = await self._cec.power_off_tv()

        if success:
            self._display_state = DisplayState.STANDBY
            self._notify_state_change()

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
        if not self._cec or not self._cec.is_available:
            return DisplayState.UNKNOWN

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

        return self._display_state

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
    def cec_devices(self) -> List[CECDevice]:
        """Get list of CEC devices."""
        if self._cec:
            return self._cec.devices
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
