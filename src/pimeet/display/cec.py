"""
HDMI-CEC controller for PiMeet.

Provides control over connected displays via HDMI-CEC.
"""

import asyncio
import logging
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class CECPowerStatus(Enum):
    """CEC device power status."""
    ON = "on"
    STANDBY = "standby"
    IN_TRANSITION_ON = "in_transition_on"
    IN_TRANSITION_STANDBY = "in_transition_standby"
    UNKNOWN = "unknown"


class CECDeviceType(Enum):
    """CEC device types."""
    TV = 0
    RECORDING = 1
    RESERVED = 2
    TUNER = 3
    PLAYBACK = 4
    AUDIO = 5


@dataclass
class CECDevice:
    """Information about a CEC device."""
    logical_address: int
    physical_address: str
    device_type: CECDeviceType
    vendor: str
    osd_name: str
    power_status: CECPowerStatus
    is_active_source: bool

    @property
    def is_tv(self) -> bool:
        return self.device_type == CECDeviceType.TV


class CECController:
    """
    HDMI-CEC controller using cec-client.

    Controls displays and other CEC-enabled devices.
    Requires libcec and cec-utils package.
    """

    def __init__(self, device: str = "/dev/cec0"):
        """
        Initialize CEC controller.

        Args:
            device: CEC device path
        """
        self._device = device
        self._available = False
        self._devices: List[CECDevice] = []
        self._tv_address = 0  # TV is always at logical address 0

    async def initialize(self) -> bool:
        """
        Initialize CEC connection.

        Returns:
            True if CEC is available and initialized
        """
        # Check for cec-client
        try:
            result = await self._run_command("cec-client", "--help")
            if result is None:
                logger.warning("cec-client not found. Install: apt install cec-utils")
                return False
        except Exception:
            logger.warning("CEC not available")
            return False

        # Check for CEC device
        try:
            from pathlib import Path
            if not Path(self._device).exists():
                logger.warning(f"CEC device not found: {self._device}")
                return False
        except Exception:
            pass

        self._available = True
        logger.info("CEC controller initialized")

        # Scan for devices
        await self.scan_devices()

        return True

    async def _run_command(self, *args, input_text: Optional[str] = None) -> Optional[str]:
        """Run a command and return output."""
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE if input_text else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_text.encode() if input_text else None),
                timeout=10.0,
            )

            if process.returncode != 0:
                logger.debug(f"CEC command failed: {stderr.decode()}")
                return None

            return stdout.decode()

        except asyncio.TimeoutError:
            logger.error("CEC command timeout")
            return None
        except Exception as e:
            logger.error(f"CEC command error: {e}")
            return None

    async def _cec_send(self, command: str) -> Optional[str]:
        """
        Send a CEC command via cec-client.

        Args:
            command: CEC command to send

        Returns:
            Command output or None on failure
        """
        if not self._available:
            return None

        # Use echo to send command to cec-client
        return await self._run_command(
            "cec-client",
            "-s",
            "-d", "1",
            input_text=f"{command}\n",
        )

    async def scan_devices(self) -> List[CECDevice]:
        """
        Scan for CEC devices on the bus.

        Returns:
            List of discovered CEC devices
        """
        if not self._available:
            return []

        self._devices.clear()

        try:
            # Send scan command
            output = await self._cec_send("scan")
            if not output:
                return []

            # Parse scan output
            current_device = None
            for line in output.split('\n'):
                line = line.strip()

                # Device header: "device #0: TV"
                match = re.match(r'device #(\d+):\s*(\w+)', line)
                if match:
                    if current_device:
                        self._devices.append(current_device)

                    addr = int(match.group(1))
                    dev_type = match.group(2).lower()

                    type_map = {
                        'tv': CECDeviceType.TV,
                        'recording': CECDeviceType.RECORDING,
                        'playback': CECDeviceType.PLAYBACK,
                        'tuner': CECDeviceType.TUNER,
                        'audio': CECDeviceType.AUDIO,
                    }

                    current_device = CECDevice(
                        logical_address=addr,
                        physical_address="",
                        device_type=type_map.get(dev_type, CECDeviceType.RESERVED),
                        vendor="",
                        osd_name="",
                        power_status=CECPowerStatus.UNKNOWN,
                        is_active_source=False,
                    )
                    continue

                if current_device:
                    # Physical address
                    if 'address:' in line.lower():
                        parts = line.split(':')
                        if len(parts) >= 2:
                            current_device.physical_address = parts[1].strip()

                    # Vendor
                    elif 'vendor:' in line.lower():
                        parts = line.split(':')
                        if len(parts) >= 2:
                            current_device.vendor = parts[1].strip()

                    # OSD name
                    elif 'osd string:' in line.lower():
                        parts = line.split(':')
                        if len(parts) >= 2:
                            current_device.osd_name = parts[1].strip()

                    # Power status
                    elif 'power status:' in line.lower():
                        status_text = line.split(':')[1].strip().lower()
                        if 'on' in status_text:
                            current_device.power_status = CECPowerStatus.ON
                        elif 'standby' in status_text:
                            current_device.power_status = CECPowerStatus.STANDBY

                    # Active source
                    elif 'active source' in line.lower():
                        current_device.is_active_source = 'yes' in line.lower()

            if current_device:
                self._devices.append(current_device)

            logger.info(f"Found {len(self._devices)} CEC devices")
            return self._devices

        except Exception as e:
            logger.error(f"CEC scan error: {e}")
            return []

    @property
    def devices(self) -> List[CECDevice]:
        """Get list of discovered CEC devices."""
        return self._devices.copy()

    @property
    def tv(self) -> Optional[CECDevice]:
        """Get the TV device."""
        return next((d for d in self._devices if d.is_tv), None)

    async def power_on_tv(self) -> bool:
        """
        Turn on the TV.

        Returns:
            True if command sent successfully
        """
        logger.info("Powering on TV")
        result = await self._cec_send("on 0")
        return result is not None

    async def power_off_tv(self) -> bool:
        """
        Put the TV in standby.

        Returns:
            True if command sent successfully
        """
        logger.info("Powering off TV")
        result = await self._cec_send("standby 0")
        return result is not None

    async def get_tv_power_status(self) -> CECPowerStatus:
        """
        Get TV power status.

        Returns:
            Current power status
        """
        output = await self._cec_send("pow 0")
        if not output:
            return CECPowerStatus.UNKNOWN

        output_lower = output.lower()
        if 'power status: on' in output_lower:
            return CECPowerStatus.ON
        elif 'power status: standby' in output_lower:
            return CECPowerStatus.STANDBY
        elif 'in transition' in output_lower:
            if 'to on' in output_lower:
                return CECPowerStatus.IN_TRANSITION_ON
            return CECPowerStatus.IN_TRANSITION_STANDBY

        return CECPowerStatus.UNKNOWN

    async def set_active_source(self) -> bool:
        """
        Set this device as the active source.

        Makes the TV switch to this HDMI input.

        Returns:
            True if command sent successfully
        """
        logger.info("Setting active source")
        result = await self._cec_send("as")
        return result is not None

    async def set_inactive_source(self) -> bool:
        """
        Release active source status.

        Returns:
            True if command sent successfully
        """
        logger.info("Releasing active source")
        result = await self._cec_send("is")
        return result is not None

    async def send_key(self, key: str) -> bool:
        """
        Send a key press to the TV.

        Args:
            key: Key name (e.g., 'up', 'down', 'select', 'exit')

        Returns:
            True if command sent successfully
        """
        # Key codes
        key_codes = {
            'select': '00',
            'up': '01',
            'down': '02',
            'left': '03',
            'right': '04',
            'exit': '0D',
            'play': '44',
            'pause': '46',
            'stop': '45',
            'rewind': '48',
            'fast_forward': '49',
            'mute': '43',
            'volume_up': '41',
            'volume_down': '42',
            'power': '40',
            'power_toggle': '6B',
        }

        code = key_codes.get(key.lower())
        if not code:
            logger.warning(f"Unknown key: {key}")
            return False

        # Send key press and release
        await self._cec_send(f"tx 10:44:{code}")
        await asyncio.sleep(0.1)
        await self._cec_send(f"tx 10:45")

        return True

    async def get_vendor_id(self, address: int = 0) -> str:
        """Get vendor ID for a device."""
        output = await self._cec_send(f"ven {address}")
        if output:
            match = re.search(r'vendor id:\s*(\w+)', output, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    async def get_osd_name(self, address: int = 0) -> str:
        """Get OSD name for a device."""
        output = await self._cec_send(f"name {address}")
        if output:
            match = re.search(r'OSD name:\s*(.+)', output, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    async def volume_up(self) -> bool:
        """Send volume up command."""
        return await self.send_key('volume_up')

    async def volume_down(self) -> bool:
        """Send volume down command."""
        return await self.send_key('volume_down')

    async def mute(self) -> bool:
        """Send mute toggle command."""
        return await self.send_key('mute')

    @property
    def is_available(self) -> bool:
        """Whether CEC is available."""
        return self._available
