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
