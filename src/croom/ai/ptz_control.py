"""
PTZ (Pan-Tilt-Zoom) camera control for Croom.

Provides unified interface for controlling PTZ cameras, including
VISCA protocol support and integration with auto-framing.
"""

import asyncio
import logging
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PTZProtocol(Enum):
    """Supported PTZ protocols."""
    VISCA = "visca"
    ONVIF = "onvif"
    PELCO_D = "pelco_d"
    HTTP = "http"
    USB = "usb"


class PTZCapability(Enum):
    """PTZ camera capabilities."""
    PAN = "pan"
    TILT = "tilt"
    ZOOM = "zoom"
    FOCUS = "focus"
    PRESET = "preset"
    HOME = "home"
    FLIP = "flip"
    MIRROR = "mirror"
    IRIS = "iris"


@dataclass
class PTZPosition:
    """PTZ camera position."""
    pan: float = 0.0  # -1.0 to 1.0
    tilt: float = 0.0  # -1.0 to 1.0
    zoom: float = 0.0  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "pan": self.pan,
            "tilt": self.tilt,
            "zoom": self.zoom,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PTZPreset:
    """PTZ preset position."""
    id: int
    name: str
    position: PTZPosition
    thumbnail: Optional[bytes] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position.to_dict(),
        }


@dataclass
class PTZLimits:
    """PTZ movement limits."""
    pan_min: float = -1.0
    pan_max: float = 1.0
    tilt_min: float = -1.0
    tilt_max: float = 1.0
    zoom_min: float = 0.0
    zoom_max: float = 1.0
    pan_speed_max: float = 1.0
    tilt_speed_max: float = 1.0
    zoom_speed_max: float = 1.0


class PTZController(ABC):
    """Abstract base class for PTZ camera controllers."""

    def __init__(self):
        self._position = PTZPosition()
        self._limits = PTZLimits()
        self._capabilities: List[PTZCapability] = []
        self._presets: Dict[int, PTZPreset] = {}
        self._connected = False

    @property
    @abstractmethod
    def protocol(self) -> PTZProtocol:
        """Get protocol type."""
        pass

    @property
    def position(self) -> PTZPosition:
        return self._position

    @property
    def limits(self) -> PTZLimits:
        return self._limits

    @property
    def capabilities(self) -> List[PTZCapability]:
        return self._capabilities

    @property
    def is_connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to PTZ camera."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from PTZ camera."""
        pass

    @abstractmethod
    async def move_to(
        self,
        pan: Optional[float] = None,
        tilt: Optional[float] = None,
        zoom: Optional[float] = None,
        speed: float = 0.5,
    ) -> bool:
        """
        Move to absolute position.

        Args:
            pan: Target pan position (-1 to 1)
            tilt: Target tilt position (-1 to 1)
            zoom: Target zoom level (0 to 1)
            speed: Movement speed (0 to 1)
        """
        pass

    @abstractmethod
    async def move_relative(
        self,
        pan_delta: float = 0,
        tilt_delta: float = 0,
        zoom_delta: float = 0,
        speed: float = 0.5,
    ) -> bool:
        """
        Move relative to current position.

        Args:
            pan_delta: Pan change
            tilt_delta: Tilt change
            zoom_delta: Zoom change
            speed: Movement speed (0 to 1)
        """
        pass

    @abstractmethod
    async def move_continuous(
        self,
        pan_speed: float = 0,
        tilt_speed: float = 0,
        zoom_speed: float = 0,
    ) -> bool:
        """
        Start continuous movement.

        Args:
            pan_speed: Pan speed (-1 to 1)
            tilt_speed: Tilt speed (-1 to 1)
            zoom_speed: Zoom speed (-1 to 1)
        """
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Stop all movement."""
        pass

    @abstractmethod
    async def go_home(self) -> bool:
        """Move to home position."""
        pass

    @abstractmethod
    async def get_position(self) -> PTZPosition:
        """Get current position."""
        pass

    async def save_preset(self, preset_id: int, name: str = "") -> bool:
        """Save current position as preset."""
        position = await self.get_position()
        self._presets[preset_id] = PTZPreset(
            id=preset_id,
            name=name or f"Preset {preset_id}",
            position=position,
        )
        return True

    async def recall_preset(self, preset_id: int) -> bool:
        """Move to saved preset position."""
        if preset_id not in self._presets:
            return False
        preset = self._presets[preset_id]
        return await self.move_to(
            pan=preset.position.pan,
            tilt=preset.position.tilt,
            zoom=preset.position.zoom,
        )

    def get_presets(self) -> List[PTZPreset]:
        """Get all presets."""
        return list(self._presets.values())


class VISCAController(PTZController):
    """VISCA protocol PTZ controller."""

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = 52381,
        camera_address: int = 1,
    ):
        super().__init__()
        self._host = host
        self._port = port
        self._camera_address = camera_address
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

        self._capabilities = [
            PTZCapability.PAN,
            PTZCapability.TILT,
            PTZCapability.ZOOM,
            PTZCapability.FOCUS,
            PTZCapability.PRESET,
            PTZCapability.HOME,
        ]

    @property
    def protocol(self) -> PTZProtocol:
        return PTZProtocol.VISCA

    async def connect(self) -> bool:
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self._host, self._port
            )
            self._connected = True
            logger.info(f"Connected to VISCA camera at {self._host}:{self._port}")

            # Get initial position
            await self.get_position()

            return True
        except Exception as e:
            logger.error(f"Failed to connect to VISCA camera: {e}")
            return False

    async def disconnect(self) -> None:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._connected = False
        logger.info("Disconnected from VISCA camera")

    async def _send_command(self, command: bytes) -> bytes:
        """Send VISCA command and receive response."""
        if not self._connected or not self._writer:
            raise RuntimeError("Not connected")

        # VISCA over IP framing
        packet = struct.pack(">HH", 0x0100, len(command)) + command

        self._writer.write(packet)
        await self._writer.drain()

        # Read response
        header = await self._reader.read(4)
        if len(header) < 4:
            return b""

        msg_type, length = struct.unpack(">HH", header)
        if length > 0:
            response = await self._reader.read(length)
            return response

        return b""

    def _build_address(self) -> int:
        """Build VISCA address byte."""
        return 0x80 | self._camera_address

    async def move_to(
        self,
        pan: Optional[float] = None,
        tilt: Optional[float] = None,
        zoom: Optional[float] = None,
        speed: float = 0.5,
    ) -> bool:
        try:
            if pan is not None or tilt is not None:
                # Absolute Pan/Tilt
                p = int((pan if pan is not None else self._position.pan) * 0x7FFF)
                t = int((tilt if tilt is not None else self._position.tilt) * 0x7FFF)
                pan_speed = int(speed * 0x18)
                tilt_speed = int(speed * 0x14)

                command = bytes([
                    self._build_address(), 0x01, 0x06, 0x02,
                    pan_speed, tilt_speed,
                    (p >> 12) & 0x0F, (p >> 8) & 0x0F, (p >> 4) & 0x0F, p & 0x0F,
                    (t >> 12) & 0x0F, (t >> 8) & 0x0F, (t >> 4) & 0x0F, t & 0x0F,
                    0xFF,
                ])
                await self._send_command(command)

            if zoom is not None:
                # Direct Zoom
                z = int(zoom * 0x4000)
                command = bytes([
                    self._build_address(), 0x01, 0x04, 0x47,
                    (z >> 12) & 0x0F, (z >> 8) & 0x0F, (z >> 4) & 0x0F, z & 0x0F,
                    0xFF,
                ])
                await self._send_command(command)

            # Update position
            await self.get_position()
            return True

        except Exception as e:
            logger.error(f"VISCA move_to error: {e}")
            return False

    async def move_relative(
        self,
        pan_delta: float = 0,
        tilt_delta: float = 0,
        zoom_delta: float = 0,
        speed: float = 0.5,
    ) -> bool:
        new_pan = self._position.pan + pan_delta
        new_tilt = self._position.tilt + tilt_delta
        new_zoom = self._position.zoom + zoom_delta

        # Clamp values
        new_pan = max(self._limits.pan_min, min(self._limits.pan_max, new_pan))
        new_tilt = max(self._limits.tilt_min, min(self._limits.tilt_max, new_tilt))
        new_zoom = max(self._limits.zoom_min, min(self._limits.zoom_max, new_zoom))

        return await self.move_to(pan=new_pan, tilt=new_tilt, zoom=new_zoom, speed=speed)

    async def move_continuous(
        self,
        pan_speed: float = 0,
        tilt_speed: float = 0,
        zoom_speed: float = 0,
    ) -> bool:
        try:
            # Pan/Tilt continuous
            if pan_speed != 0 or tilt_speed != 0:
                ps = 0x00 if pan_speed == 0 else (0x01 if pan_speed > 0 else 0x02)
                ts = 0x00 if tilt_speed == 0 else (0x01 if tilt_speed > 0 else 0x02)
                ps_val = int(abs(pan_speed) * 0x18)
                ts_val = int(abs(tilt_speed) * 0x14)

                if pan_speed == 0 and tilt_speed == 0:
                    # Stop
                    command = bytes([
                        self._build_address(), 0x01, 0x06, 0x01,
                        0x00, 0x00, 0x03, 0x03, 0xFF,
                    ])
                else:
                    pan_dir = 0x02 if pan_speed > 0 else 0x01
                    tilt_dir = 0x02 if tilt_speed > 0 else 0x01
                    command = bytes([
                        self._build_address(), 0x01, 0x06, 0x01,
                        max(1, ps_val), max(1, ts_val), pan_dir, tilt_dir, 0xFF,
                    ])
                await self._send_command(command)

            # Zoom continuous
            if zoom_speed != 0:
                if zoom_speed > 0:
                    zs = 0x20 | int(zoom_speed * 7)  # Tele
                else:
                    zs = 0x30 | int(abs(zoom_speed) * 7)  # Wide
                command = bytes([
                    self._build_address(), 0x01, 0x04, 0x07, zs, 0xFF,
                ])
                await self._send_command(command)

            return True

        except Exception as e:
            logger.error(f"VISCA move_continuous error: {e}")
            return False

    async def stop(self) -> bool:
        try:
            # Stop Pan/Tilt
            command = bytes([
                self._build_address(), 0x01, 0x06, 0x01,
                0x00, 0x00, 0x03, 0x03, 0xFF,
            ])
            await self._send_command(command)

            # Stop Zoom
            command = bytes([
                self._build_address(), 0x01, 0x04, 0x07, 0x00, 0xFF,
            ])
            await self._send_command(command)

            return True
        except Exception as e:
            logger.error(f"VISCA stop error: {e}")
            return False

    async def go_home(self) -> bool:
        try:
            command = bytes([
                self._build_address(), 0x01, 0x06, 0x04, 0xFF,
            ])
            await self._send_command(command)
            await self.get_position()
            return True
        except Exception as e:
            logger.error(f"VISCA go_home error: {e}")
            return False

    async def get_position(self) -> PTZPosition:
        try:
            # Inquiry Pan/Tilt position
            command = bytes([
                self._build_address(), 0x09, 0x06, 0x12, 0xFF,
            ])
            response = await self._send_command(command)

            if len(response) >= 11:
                pan_raw = (
                    (response[2] << 12) | (response[3] << 8) |
                    (response[4] << 4) | response[5]
                )
                tilt_raw = (
                    (response[6] << 12) | (response[7] << 8) |
                    (response[8] << 4) | response[9]
                )

                # Convert to signed
                if pan_raw > 0x7FFF:
                    pan_raw -= 0x10000
                if tilt_raw > 0x7FFF:
                    tilt_raw -= 0x10000

                self._position.pan = pan_raw / 0x7FFF
                self._position.tilt = tilt_raw / 0x7FFF

            # Inquiry Zoom position
            command = bytes([
                self._build_address(), 0x09, 0x04, 0x47, 0xFF,
            ])
            response = await self._send_command(command)

            if len(response) >= 5:
                zoom_raw = (
                    (response[2] << 12) | (response[3] << 8) |
                    (response[4] << 4) | response[5]
                )
                self._position.zoom = zoom_raw / 0x4000

            self._position.timestamp = datetime.utcnow()
            return self._position

        except Exception as e:
            logger.error(f"VISCA get_position error: {e}")
            return self._position


class SoftwarePTZController(PTZController):
    """Software-based PTZ using digital crop/zoom."""

    def __init__(
        self,
        frame_width: int = 1920,
        frame_height: int = 1080,
    ):
        super().__init__()
        self._frame_width = frame_width
        self._frame_height = frame_height
        self._connected = True

        self._capabilities = [
            PTZCapability.PAN,
            PTZCapability.TILT,
            PTZCapability.ZOOM,
        ]

        # Smooth movement
        self._target_position = PTZPosition()
        self._movement_speed = 0.1

    @property
    def protocol(self) -> PTZProtocol:
        return PTZProtocol.USB

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def move_to(
        self,
        pan: Optional[float] = None,
        tilt: Optional[float] = None,
        zoom: Optional[float] = None,
        speed: float = 0.5,
    ) -> bool:
        if pan is not None:
            self._target_position.pan = max(-1, min(1, pan))
        if tilt is not None:
            self._target_position.tilt = max(-1, min(1, tilt))
        if zoom is not None:
            self._target_position.zoom = max(0, min(1, zoom))

        self._movement_speed = speed
        return True

    async def move_relative(
        self,
        pan_delta: float = 0,
        tilt_delta: float = 0,
        zoom_delta: float = 0,
        speed: float = 0.5,
    ) -> bool:
        return await self.move_to(
            pan=self._position.pan + pan_delta,
            tilt=self._position.tilt + tilt_delta,
            zoom=self._position.zoom + zoom_delta,
            speed=speed,
        )

    async def move_continuous(
        self,
        pan_speed: float = 0,
        tilt_speed: float = 0,
        zoom_speed: float = 0,
    ) -> bool:
        # Continuous movement is handled by update loop
        return True

    async def stop(self) -> bool:
        self._target_position = PTZPosition(
            pan=self._position.pan,
            tilt=self._position.tilt,
            zoom=self._position.zoom,
        )
        return True

    async def go_home(self) -> bool:
        return await self.move_to(pan=0, tilt=0, zoom=0)

    async def get_position(self) -> PTZPosition:
        return self._position

    def update(self, dt: float = 0.033) -> None:
        """Update position towards target (call each frame)."""
        alpha = self._movement_speed * dt * 30

        self._position.pan += (self._target_position.pan - self._position.pan) * alpha
        self._position.tilt += (self._target_position.tilt - self._position.tilt) * alpha
        self._position.zoom += (self._target_position.zoom - self._position.zoom) * alpha
        self._position.timestamp = datetime.utcnow()

    def get_crop_region(self) -> Tuple[int, int, int, int]:
        """Get crop region for software zoom."""
        # Zoom determines crop size
        scale = 1.0 / (1.0 + self._position.zoom * 2)

        crop_width = int(self._frame_width * scale)
        crop_height = int(self._frame_height * scale)

        # Pan/tilt determine crop position
        center_x = self._frame_width / 2 + self._position.pan * (self._frame_width - crop_width) / 2
        center_y = self._frame_height / 2 + self._position.tilt * (self._frame_height - crop_height) / 2

        x1 = int(center_x - crop_width / 2)
        y1 = int(center_y - crop_height / 2)
        x2 = int(center_x + crop_width / 2)
        y2 = int(center_y + crop_height / 2)

        # Clamp
        x1 = max(0, min(self._frame_width - crop_width, x1))
        y1 = max(0, min(self._frame_height - crop_height, y1))
        x2 = x1 + crop_width
        y2 = y1 + crop_height

        return (x1, y1, x2, y2)


class ONVIFController(PTZController):
    """ONVIF protocol PTZ controller for IP cameras."""

    def __init__(
        self,
        host: str,
        port: int = 80,
        username: str = "admin",
        password: str = "",
        profile_token: Optional[str] = None,
    ):
        super().__init__()
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._profile_token = profile_token

        # ONVIF services
        self._device_service = None
        self._ptz_service = None
        self._media_service = None
        self._imaging_service = None

        self._capabilities = [
            PTZCapability.PAN,
            PTZCapability.TILT,
            PTZCapability.ZOOM,
            PTZCapability.PRESET,
            PTZCapability.HOME,
        ]

    @property
    def protocol(self) -> PTZProtocol:
        return PTZProtocol.ONVIF

    async def connect(self) -> bool:
        """Connect to ONVIF camera and discover services."""
        try:
            from onvif import ONVIFCamera
        except ImportError:
            logger.error("onvif-zeep library not installed. Install with: pip install onvif-zeep")
            return False

        try:
            # Create ONVIF camera instance
            loop = asyncio.get_event_loop()
            self._camera = await loop.run_in_executor(
                None,
                lambda: ONVIFCamera(
                    self._host,
                    self._port,
                    self._username,
                    self._password,
                )
            )

            # Get services
            self._device_service = self._camera.devicemgmt
            self._media_service = await loop.run_in_executor(
                None, self._camera.create_media_service
            )
            self._ptz_service = await loop.run_in_executor(
                None, self._camera.create_ptz_service
            )

            # Get profile token if not provided
            if not self._profile_token:
                profiles = await loop.run_in_executor(
                    None, self._media_service.GetProfiles
                )
                if profiles:
                    self._profile_token = profiles[0].token

            # Get PTZ configuration space for limits
            try:
                config_options = await loop.run_in_executor(
                    None,
                    lambda: self._ptz_service.GetConfigurationOptions({
                        'ConfigurationToken': self._profile_token
                    })
                )
                if config_options:
                    spaces = config_options.Spaces
                    if hasattr(spaces, 'AbsolutePanTiltPositionSpace'):
                        space = spaces.AbsolutePanTiltPositionSpace[0]
                        self._limits.pan_min = space.XRange.Min
                        self._limits.pan_max = space.XRange.Max
                        self._limits.tilt_min = space.YRange.Min
                        self._limits.tilt_max = space.YRange.Max
            except Exception:
                pass

            self._connected = True
            logger.info(f"Connected to ONVIF camera at {self._host}:{self._port}")

            # Get initial position
            await self.get_position()
            return True

        except Exception as e:
            logger.error(f"Failed to connect to ONVIF camera: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from camera."""
        self._connected = False
        self._camera = None
        self._ptz_service = None
        logger.info("Disconnected from ONVIF camera")

    async def move_to(
        self,
        pan: Optional[float] = None,
        tilt: Optional[float] = None,
        zoom: Optional[float] = None,
        speed: float = 0.5,
    ) -> bool:
        if not self._connected or not self._ptz_service:
            return False

        try:
            loop = asyncio.get_event_loop()

            request = {
                'ProfileToken': self._profile_token,
                'Position': {},
                'Speed': {},
            }

            if pan is not None or tilt is not None:
                request['Position']['PanTilt'] = {
                    'x': pan if pan is not None else self._position.pan,
                    'y': tilt if tilt is not None else self._position.tilt,
                }
                request['Speed']['PanTilt'] = {'x': speed, 'y': speed}

            if zoom is not None:
                request['Position']['Zoom'] = {'x': zoom}
                request['Speed']['Zoom'] = {'x': speed}

            await loop.run_in_executor(
                None,
                lambda: self._ptz_service.AbsoluteMove(request)
            )

            await self.get_position()
            return True

        except Exception as e:
            logger.error(f"ONVIF move_to error: {e}")
            return False

    async def move_relative(
        self,
        pan_delta: float = 0,
        tilt_delta: float = 0,
        zoom_delta: float = 0,
        speed: float = 0.5,
    ) -> bool:
        if not self._connected or not self._ptz_service:
            return False

        try:
            loop = asyncio.get_event_loop()

            request = {
                'ProfileToken': self._profile_token,
                'Translation': {},
                'Speed': {},
            }

            if pan_delta != 0 or tilt_delta != 0:
                request['Translation']['PanTilt'] = {'x': pan_delta, 'y': tilt_delta}
                request['Speed']['PanTilt'] = {'x': speed, 'y': speed}

            if zoom_delta != 0:
                request['Translation']['Zoom'] = {'x': zoom_delta}
                request['Speed']['Zoom'] = {'x': speed}

            await loop.run_in_executor(
                None,
                lambda: self._ptz_service.RelativeMove(request)
            )

            await self.get_position()
            return True

        except Exception as e:
            logger.error(f"ONVIF move_relative error: {e}")
            return False

    async def move_continuous(
        self,
        pan_speed: float = 0,
        tilt_speed: float = 0,
        zoom_speed: float = 0,
    ) -> bool:
        if not self._connected or not self._ptz_service:
            return False

        try:
            loop = asyncio.get_event_loop()

            request = {
                'ProfileToken': self._profile_token,
                'Velocity': {},
            }

            if pan_speed != 0 or tilt_speed != 0:
                request['Velocity']['PanTilt'] = {'x': pan_speed, 'y': tilt_speed}

            if zoom_speed != 0:
                request['Velocity']['Zoom'] = {'x': zoom_speed}

            await loop.run_in_executor(
                None,
                lambda: self._ptz_service.ContinuousMove(request)
            )
            return True

        except Exception as e:
            logger.error(f"ONVIF move_continuous error: {e}")
            return False

    async def stop(self) -> bool:
        if not self._connected or not self._ptz_service:
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._ptz_service.Stop({
                    'ProfileToken': self._profile_token,
                    'PanTilt': True,
                    'Zoom': True,
                })
            )
            return True
        except Exception as e:
            logger.error(f"ONVIF stop error: {e}")
            return False

    async def go_home(self) -> bool:
        if not self._connected or not self._ptz_service:
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._ptz_service.GotoHomePosition({
                    'ProfileToken': self._profile_token,
                })
            )
            await self.get_position()
            return True
        except Exception as e:
            logger.error(f"ONVIF go_home error: {e}")
            return False

    async def get_position(self) -> PTZPosition:
        if not self._connected or not self._ptz_service:
            return self._position

        try:
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(
                None,
                lambda: self._ptz_service.GetStatus({
                    'ProfileToken': self._profile_token,
                })
            )

            if status and hasattr(status, 'Position'):
                pos = status.Position
                if hasattr(pos, 'PanTilt'):
                    self._position.pan = pos.PanTilt.x
                    self._position.tilt = pos.PanTilt.y
                if hasattr(pos, 'Zoom'):
                    self._position.zoom = pos.Zoom.x

            self._position.timestamp = datetime.utcnow()

        except Exception as e:
            logger.error(f"ONVIF get_position error: {e}")

        return self._position


class PelcoDController(PTZController):
    """Pelco-D protocol PTZ controller for serial cameras."""

    # Pelco-D commands
    CMD_PAN_LEFT = 0x04
    CMD_PAN_RIGHT = 0x02
    CMD_TILT_UP = 0x08
    CMD_TILT_DOWN = 0x10
    CMD_ZOOM_TELE = 0x20
    CMD_ZOOM_WIDE = 0x40
    CMD_PRESET_SET = 0x03
    CMD_PRESET_CALL = 0x07
    CMD_PRESET_CLEAR = 0x05

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        camera_address: int = 1,
    ):
        super().__init__()
        self._port = port
        self._baudrate = baudrate
        self._camera_address = camera_address
        self._serial = None

        self._capabilities = [
            PTZCapability.PAN,
            PTZCapability.TILT,
            PTZCapability.ZOOM,
            PTZCapability.PRESET,
        ]

    @property
    def protocol(self) -> PTZProtocol:
        return PTZProtocol.PELCO_D

    async def connect(self) -> bool:
        try:
            import serial
        except ImportError:
            logger.error("pyserial library not installed. Install with: pip install pyserial")
            return False

        try:
            loop = asyncio.get_event_loop()
            self._serial = await loop.run_in_executor(
                None,
                lambda: serial.Serial(
                    self._port,
                    self._baudrate,
                    timeout=1,
                )
            )
            self._connected = True
            logger.info(f"Connected to Pelco-D camera on {self._port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Pelco-D camera: {e}")
            return False

    async def disconnect(self) -> None:
        if self._serial:
            self._serial.close()
            self._serial = None
        self._connected = False
        logger.info("Disconnected from Pelco-D camera")

    def _build_command(self, cmd1: int, cmd2: int, data1: int = 0, data2: int = 0) -> bytes:
        """Build Pelco-D command packet."""
        sync = 0xFF
        addr = self._camera_address
        checksum = (addr + cmd1 + cmd2 + data1 + data2) % 256
        return bytes([sync, addr, cmd1, cmd2, data1, data2, checksum])

    async def _send_command(self, cmd1: int, cmd2: int, data1: int = 0, data2: int = 0) -> bool:
        if not self._serial:
            return False

        try:
            packet = self._build_command(cmd1, cmd2, data1, data2)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._serial.write, packet)
            return True
        except Exception as e:
            logger.error(f"Pelco-D command error: {e}")
            return False

    async def move_to(
        self,
        pan: Optional[float] = None,
        tilt: Optional[float] = None,
        zoom: Optional[float] = None,
        speed: float = 0.5,
    ) -> bool:
        # Pelco-D doesn't support absolute positioning
        # We'll move continuously for a calculated time
        pan_speed = int(speed * 0x3F)
        tilt_speed = int(speed * 0x3F)

        if pan is not None:
            delta = pan - self._position.pan
            if abs(delta) > 0.01:
                cmd = self.CMD_PAN_RIGHT if delta > 0 else self.CMD_PAN_LEFT
                await self._send_command(0x00, cmd, pan_speed, 0)
                await asyncio.sleep(abs(delta) * 2)  # Approximate timing
                await self.stop()

        if tilt is not None:
            delta = tilt - self._position.tilt
            if abs(delta) > 0.01:
                cmd = self.CMD_TILT_UP if delta > 0 else self.CMD_TILT_DOWN
                await self._send_command(0x00, cmd, 0, tilt_speed)
                await asyncio.sleep(abs(delta) * 2)
                await self.stop()

        if zoom is not None:
            delta = zoom - self._position.zoom
            if abs(delta) > 0.01:
                cmd = self.CMD_ZOOM_TELE if delta > 0 else self.CMD_ZOOM_WIDE
                await self._send_command(0x00, cmd, 0, 0)
                await asyncio.sleep(abs(delta) * 3)
                await self.stop()

        # Update estimated position
        if pan is not None:
            self._position.pan = pan
        if tilt is not None:
            self._position.tilt = tilt
        if zoom is not None:
            self._position.zoom = zoom

        return True

    async def move_relative(
        self,
        pan_delta: float = 0,
        tilt_delta: float = 0,
        zoom_delta: float = 0,
        speed: float = 0.5,
    ) -> bool:
        return await self.move_to(
            pan=self._position.pan + pan_delta if pan_delta else None,
            tilt=self._position.tilt + tilt_delta if tilt_delta else None,
            zoom=self._position.zoom + zoom_delta if zoom_delta else None,
            speed=speed,
        )

    async def move_continuous(
        self,
        pan_speed: float = 0,
        tilt_speed: float = 0,
        zoom_speed: float = 0,
    ) -> bool:
        cmd2 = 0
        data1 = 0
        data2 = 0

        if pan_speed > 0:
            cmd2 |= self.CMD_PAN_RIGHT
            data1 = int(abs(pan_speed) * 0x3F)
        elif pan_speed < 0:
            cmd2 |= self.CMD_PAN_LEFT
            data1 = int(abs(pan_speed) * 0x3F)

        if tilt_speed > 0:
            cmd2 |= self.CMD_TILT_UP
            data2 = int(abs(tilt_speed) * 0x3F)
        elif tilt_speed < 0:
            cmd2 |= self.CMD_TILT_DOWN
            data2 = int(abs(tilt_speed) * 0x3F)

        if zoom_speed > 0:
            cmd2 |= self.CMD_ZOOM_TELE
        elif zoom_speed < 0:
            cmd2 |= self.CMD_ZOOM_WIDE

        return await self._send_command(0x00, cmd2, data1, data2)

    async def stop(self) -> bool:
        return await self._send_command(0x00, 0x00, 0x00, 0x00)

    async def go_home(self) -> bool:
        # Call preset 0 (usually home)
        return await self._send_command(0x00, self.CMD_PRESET_CALL, 0x00, 0x00)

    async def get_position(self) -> PTZPosition:
        # Pelco-D doesn't support position queries
        return self._position

    async def save_preset(self, preset_id: int, name: str = "") -> bool:
        success = await self._send_command(0x00, self.CMD_PRESET_SET, 0x00, preset_id)
        if success:
            await super().save_preset(preset_id, name)
        return success

    async def recall_preset(self, preset_id: int) -> bool:
        return await self._send_command(0x00, self.CMD_PRESET_CALL, 0x00, preset_id)


class HTTPPTZController(PTZController):
    """HTTP/REST API PTZ controller for IP cameras."""

    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        endpoints: Optional[Dict[str, str]] = None,
    ):
        super().__init__()
        self._base_url = base_url.rstrip('/')
        self._username = username
        self._password = password
        self._session: Optional[Any] = None

        # Default endpoint patterns (can be customized per camera model)
        self._endpoints = endpoints or {
            'move_to': '/ptz/move',
            'move_relative': '/ptz/relative',
            'move_continuous': '/ptz/continuous',
            'stop': '/ptz/stop',
            'home': '/ptz/home',
            'position': '/ptz/position',
            'preset_set': '/ptz/preset/set',
            'preset_call': '/ptz/preset/call',
        }

        self._capabilities = [
            PTZCapability.PAN,
            PTZCapability.TILT,
            PTZCapability.ZOOM,
            PTZCapability.PRESET,
            PTZCapability.HOME,
        ]

    @property
    def protocol(self) -> PTZProtocol:
        return PTZProtocol.HTTP

    async def connect(self) -> bool:
        try:
            import aiohttp

            auth = None
            if self._username and self._password:
                auth = aiohttp.BasicAuth(self._username, self._password)

            self._session = aiohttp.ClientSession(auth=auth)

            # Test connection by getting position
            async with self._session.get(
                f"{self._base_url}{self._endpoints['position']}",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    self._connected = True
                    logger.info(f"Connected to HTTP PTZ camera at {self._base_url}")
                    await self.get_position()
                    return True
                else:
                    logger.error(f"HTTP PTZ connection failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Failed to connect to HTTP PTZ camera: {e}")
            return False

    async def disconnect(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        self._connected = False
        logger.info("Disconnected from HTTP PTZ camera")

    async def _post(self, endpoint: str, data: Dict[str, Any]) -> bool:
        if not self._session:
            return False

        try:
            import aiohttp
            async with self._session.post(
                f"{self._base_url}{endpoint}",
                json=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                return response.status in (200, 201, 204)
        except Exception as e:
            logger.error(f"HTTP PTZ request error: {e}")
            return False

    async def _get(self, endpoint: str) -> Optional[Dict[str, Any]]:
        if not self._session:
            return None

        try:
            import aiohttp
            async with self._session.get(
                f"{self._base_url}{endpoint}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"HTTP PTZ request error: {e}")
        return None

    async def move_to(
        self,
        pan: Optional[float] = None,
        tilt: Optional[float] = None,
        zoom: Optional[float] = None,
        speed: float = 0.5,
    ) -> bool:
        data = {'speed': speed}
        if pan is not None:
            data['pan'] = pan
        if tilt is not None:
            data['tilt'] = tilt
        if zoom is not None:
            data['zoom'] = zoom

        success = await self._post(self._endpoints['move_to'], data)
        if success:
            await self.get_position()
        return success

    async def move_relative(
        self,
        pan_delta: float = 0,
        tilt_delta: float = 0,
        zoom_delta: float = 0,
        speed: float = 0.5,
    ) -> bool:
        data = {
            'pan_delta': pan_delta,
            'tilt_delta': tilt_delta,
            'zoom_delta': zoom_delta,
            'speed': speed,
        }
        success = await self._post(self._endpoints['move_relative'], data)
        if success:
            await self.get_position()
        return success

    async def move_continuous(
        self,
        pan_speed: float = 0,
        tilt_speed: float = 0,
        zoom_speed: float = 0,
    ) -> bool:
        data = {
            'pan_speed': pan_speed,
            'tilt_speed': tilt_speed,
            'zoom_speed': zoom_speed,
        }
        return await self._post(self._endpoints['move_continuous'], data)

    async def stop(self) -> bool:
        return await self._post(self._endpoints['stop'], {})

    async def go_home(self) -> bool:
        success = await self._post(self._endpoints['home'], {})
        if success:
            await self.get_position()
        return success

    async def get_position(self) -> PTZPosition:
        data = await self._get(self._endpoints['position'])
        if data:
            self._position.pan = data.get('pan', self._position.pan)
            self._position.tilt = data.get('tilt', self._position.tilt)
            self._position.zoom = data.get('zoom', self._position.zoom)
        self._position.timestamp = datetime.utcnow()
        return self._position

    async def save_preset(self, preset_id: int, name: str = "") -> bool:
        success = await self._post(self._endpoints['preset_set'], {
            'preset_id': preset_id,
            'name': name,
        })
        if success:
            await super().save_preset(preset_id, name)
        return success

    async def recall_preset(self, preset_id: int) -> bool:
        success = await self._post(self._endpoints['preset_call'], {
            'preset_id': preset_id,
        })
        if success:
            await self.get_position()
        return success


def create_ptz_controller(
    protocol: PTZProtocol,
    **kwargs,
) -> PTZController:
    """
    Factory function to create PTZ controller by protocol.

    Args:
        protocol: PTZ protocol type
        **kwargs: Protocol-specific arguments

    Returns:
        Configured PTZController instance
    """
    controllers = {
        PTZProtocol.VISCA: VISCAController,
        PTZProtocol.ONVIF: ONVIFController,
        PTZProtocol.PELCO_D: PelcoDController,
        PTZProtocol.HTTP: HTTPPTZController,
        PTZProtocol.USB: SoftwarePTZController,
    }

    controller_cls = controllers.get(protocol, SoftwarePTZController)
    return controller_cls(**kwargs)


class PTZService:
    """High-level PTZ control service with auto-framing integration."""

    def __init__(
        self,
        controller: Optional[PTZController] = None,
        auto_framing_engine=None,
    ):
        self._controller = controller or SoftwarePTZController()
        self._auto_framing = auto_framing_engine
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Integration mode
        self._auto_framing_enabled = True

        # Connect auto-framing callbacks
        if self._auto_framing:
            self._auto_framing.on_region_change(self._on_framing_region_change)

    async def start(self) -> None:
        """Start PTZ service."""
        if self._running:
            return

        await self._controller.connect()
        self._running = True
        self._task = asyncio.create_task(self._update_loop())
        logger.info("PTZ service started")

    async def stop(self) -> None:
        """Stop PTZ service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._controller.disconnect()
        logger.info("PTZ service stopped")

    async def _update_loop(self) -> None:
        """Main update loop."""
        while self._running:
            try:
                # Update software PTZ
                if isinstance(self._controller, SoftwarePTZController):
                    self._controller.update(0.033)

            except Exception as e:
                logger.error(f"PTZ update error: {e}")

            await asyncio.sleep(0.033)

    def _on_framing_region_change(self, region) -> None:
        """Handle auto-framing region change."""
        if not self._auto_framing_enabled:
            return

        # Convert region to PTZ position
        center_x, center_y = region.center

        # Map center to pan/tilt (-1 to 1)
        pan = (center_x - 0.5) * 2
        tilt = (center_y - 0.5) * 2

        # Map zoom
        zoom = max(0, min(1, region.zoom - 1))

        # Queue movement
        asyncio.create_task(self._controller.move_to(
            pan=pan,
            tilt=tilt,
            zoom=zoom,
            speed=0.3,
        ))

    @property
    def controller(self) -> PTZController:
        return self._controller

    @property
    def auto_framing_enabled(self) -> bool:
        return self._auto_framing_enabled

    @auto_framing_enabled.setter
    def auto_framing_enabled(self, value: bool) -> None:
        self._auto_framing_enabled = value

    async def move_to(self, pan: float, tilt: float, zoom: float = 0) -> bool:
        return await self._controller.move_to(pan=pan, tilt=tilt, zoom=zoom)

    async def go_home(self) -> bool:
        return await self._controller.go_home()

    async def recall_preset(self, preset_id: int) -> bool:
        return await self._controller.recall_preset(preset_id)

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self._controller.is_connected,
            "protocol": self._controller.protocol.value,
            "position": self._controller.position.to_dict(),
            "capabilities": [c.value for c in self._controller.capabilities],
            "auto_framing_enabled": self._auto_framing_enabled,
            "presets": [p.to_dict() for p in self._controller.get_presets()],
        }
