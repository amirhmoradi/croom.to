"""
IR Remote Navigation for Croom Touch UI.

Provides support for controlling the Croom UI using standard
TV/AV IR remotes (Samsung, LG, Sony, etc.).

Features:
- LIRC integration for IR decoding
- Configurable keymaps
- Focus-based navigation
- Meeting controls mapping
- Volume/media controls
"""

import asyncio
import logging
import os
import socket
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class IRAction(Enum):
    """IR remote actions."""
    # Navigation
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    OK = "ok"
    BACK = "back"
    HOME = "home"
    MENU = "menu"

    # Media controls
    PLAY_PAUSE = "play_pause"
    STOP = "stop"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    MUTE = "mute"

    # Meeting controls
    TOGGLE_CAMERA = "toggle_camera"
    TOGGLE_MIC = "toggle_mic"
    LEAVE_MEETING = "leave_meeting"
    RAISE_HAND = "raise_hand"
    SHARE_SCREEN = "share_screen"

    # Numbers (for PIN entry, quick dial)
    NUM_0 = "num_0"
    NUM_1 = "num_1"
    NUM_2 = "num_2"
    NUM_3 = "num_3"
    NUM_4 = "num_4"
    NUM_5 = "num_5"
    NUM_6 = "num_6"
    NUM_7 = "num_7"
    NUM_8 = "num_8"
    NUM_9 = "num_9"

    # Colors (often available on remotes)
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"


@dataclass
class IRKeymap:
    """IR remote keymap configuration."""
    name: str
    remote_type: str
    mappings: Dict[str, IRAction] = field(default_factory=dict)
    repeat_delay: int = 200  # ms before repeat starts
    repeat_rate: int = 100   # ms between repeats


# Built-in keymaps for common remotes
SAMSUNG_KEYMAP = IRKeymap(
    name="Samsung TV Remote",
    remote_type="samsung",
    mappings={
        "KEY_UP": IRAction.UP,
        "KEY_DOWN": IRAction.DOWN,
        "KEY_LEFT": IRAction.LEFT,
        "KEY_RIGHT": IRAction.RIGHT,
        "KEY_ENTER": IRAction.OK,
        "KEY_OK": IRAction.OK,
        "KEY_BACK": IRAction.BACK,
        "KEY_EXIT": IRAction.BACK,
        "KEY_HOME": IRAction.HOME,
        "KEY_MENU": IRAction.MENU,
        "KEY_PLAYPAUSE": IRAction.PLAY_PAUSE,
        "KEY_PLAY": IRAction.PLAY_PAUSE,
        "KEY_PAUSE": IRAction.PLAY_PAUSE,
        "KEY_STOP": IRAction.STOP,
        "KEY_VOLUMEUP": IRAction.VOLUME_UP,
        "KEY_VOLUMEDOWN": IRAction.VOLUME_DOWN,
        "KEY_MUTE": IRAction.MUTE,
        "KEY_0": IRAction.NUM_0,
        "KEY_1": IRAction.NUM_1,
        "KEY_2": IRAction.NUM_2,
        "KEY_3": IRAction.NUM_3,
        "KEY_4": IRAction.NUM_4,
        "KEY_5": IRAction.NUM_5,
        "KEY_6": IRAction.NUM_6,
        "KEY_7": IRAction.NUM_7,
        "KEY_8": IRAction.NUM_8,
        "KEY_9": IRAction.NUM_9,
        "KEY_RED": IRAction.RED,
        "KEY_GREEN": IRAction.GREEN,
        "KEY_YELLOW": IRAction.YELLOW,
        "KEY_BLUE": IRAction.BLUE,
        # Samsung-specific button mappings for meeting controls
        "KEY_RECORD": IRAction.TOGGLE_MIC,
        "KEY_CAMERA": IRAction.TOGGLE_CAMERA,
    },
)

LG_KEYMAP = IRKeymap(
    name="LG TV Remote",
    remote_type="lg",
    mappings={
        "KEY_UP": IRAction.UP,
        "KEY_DOWN": IRAction.DOWN,
        "KEY_LEFT": IRAction.LEFT,
        "KEY_RIGHT": IRAction.RIGHT,
        "KEY_OK": IRAction.OK,
        "KEY_BACK": IRAction.BACK,
        "KEY_HOME": IRAction.HOME,
        "KEY_SETTINGS": IRAction.MENU,
        "KEY_VOLUMEUP": IRAction.VOLUME_UP,
        "KEY_VOLUMEDOWN": IRAction.VOLUME_DOWN,
        "KEY_MUTE": IRAction.MUTE,
        "KEY_0": IRAction.NUM_0,
        "KEY_1": IRAction.NUM_1,
        "KEY_2": IRAction.NUM_2,
        "KEY_3": IRAction.NUM_3,
        "KEY_4": IRAction.NUM_4,
        "KEY_5": IRAction.NUM_5,
        "KEY_6": IRAction.NUM_6,
        "KEY_7": IRAction.NUM_7,
        "KEY_8": IRAction.NUM_8,
        "KEY_9": IRAction.NUM_9,
        "KEY_RED": IRAction.RED,
        "KEY_GREEN": IRAction.GREEN,
        "KEY_YELLOW": IRAction.YELLOW,
        "KEY_BLUE": IRAction.BLUE,
    },
)

SONY_KEYMAP = IRKeymap(
    name="Sony TV Remote",
    remote_type="sony",
    mappings={
        "KEY_UP": IRAction.UP,
        "KEY_DOWN": IRAction.DOWN,
        "KEY_LEFT": IRAction.LEFT,
        "KEY_RIGHT": IRAction.RIGHT,
        "KEY_SELECT": IRAction.OK,
        "KEY_ENTER": IRAction.OK,
        "KEY_RETURN": IRAction.BACK,
        "KEY_BACK": IRAction.BACK,
        "KEY_HOME": IRAction.HOME,
        "KEY_MENU": IRAction.MENU,
        "KEY_VOLUMEUP": IRAction.VOLUME_UP,
        "KEY_VOLUMEDOWN": IRAction.VOLUME_DOWN,
        "KEY_MUTE": IRAction.MUTE,
        "KEY_0": IRAction.NUM_0,
        "KEY_1": IRAction.NUM_1,
        "KEY_2": IRAction.NUM_2,
        "KEY_3": IRAction.NUM_3,
        "KEY_4": IRAction.NUM_4,
        "KEY_5": IRAction.NUM_5,
        "KEY_6": IRAction.NUM_6,
        "KEY_7": IRAction.NUM_7,
        "KEY_8": IRAction.NUM_8,
        "KEY_9": IRAction.NUM_9,
        "KEY_RED": IRAction.RED,
        "KEY_GREEN": IRAction.GREEN,
        "KEY_YELLOW": IRAction.YELLOW,
        "KEY_BLUE": IRAction.BLUE,
    },
)

CROOM_KEYMAP = IRKeymap(
    name="Croom Custom Remote",
    remote_type="croom",
    mappings={
        # Standard navigation
        "KEY_UP": IRAction.UP,
        "KEY_DOWN": IRAction.DOWN,
        "KEY_LEFT": IRAction.LEFT,
        "KEY_RIGHT": IRAction.RIGHT,
        "KEY_OK": IRAction.OK,
        "KEY_BACK": IRAction.BACK,
        "KEY_HOME": IRAction.HOME,
        "KEY_MENU": IRAction.MENU,
        # Volume
        "KEY_VOLUMEUP": IRAction.VOLUME_UP,
        "KEY_VOLUMEDOWN": IRAction.VOLUME_DOWN,
        "KEY_MUTE": IRAction.MUTE,
        # Meeting-specific keys
        "KEY_MIC": IRAction.TOGGLE_MIC,
        "KEY_CAMERA": IRAction.TOGGLE_CAMERA,
        "KEY_HANGUP": IRAction.LEAVE_MEETING,
        "KEY_HAND": IRAction.RAISE_HAND,
        "KEY_SHARE": IRAction.SHARE_SCREEN,
        # Numbers
        "KEY_0": IRAction.NUM_0,
        "KEY_1": IRAction.NUM_1,
        "KEY_2": IRAction.NUM_2,
        "KEY_3": IRAction.NUM_3,
        "KEY_4": IRAction.NUM_4,
        "KEY_5": IRAction.NUM_5,
        "KEY_6": IRAction.NUM_6,
        "KEY_7": IRAction.NUM_7,
        "KEY_8": IRAction.NUM_8,
        "KEY_9": IRAction.NUM_9,
        # Function colors
        "KEY_RED": IRAction.RED,
        "KEY_GREEN": IRAction.GREEN,
        "KEY_YELLOW": IRAction.YELLOW,
        "KEY_BLUE": IRAction.BLUE,
    },
)

BUILTIN_KEYMAPS = {
    "samsung": SAMSUNG_KEYMAP,
    "lg": LG_KEYMAP,
    "sony": SONY_KEYMAP,
    "croom": CROOM_KEYMAP,
}


class LIRCClient:
    """
    LIRC (Linux Infrared Remote Control) client.

    Connects to lircd socket and receives IR key events.
    """

    def __init__(
        self,
        socket_path: str = "/var/run/lirc/lircd",
        timeout: float = 0.1
    ):
        self._socket_path = socket_path
        self._timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to LIRC daemon."""
        try:
            if not os.path.exists(self._socket_path):
                logger.error(f"LIRC socket not found: {self._socket_path}")
                return False

            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.setblocking(False)
            self._socket.settimeout(self._timeout)

            # Run blocking connect in thread
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._socket.connect,
                self._socket_path
            )

            self._connected = True
            logger.info("Connected to LIRC daemon")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to LIRC: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from LIRC daemon."""
        if self._socket:
            self._socket.close()
            self._socket = None
        self._connected = False
        logger.info("Disconnected from LIRC daemon")

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def read_key(self) -> Optional[tuple]:
        """
        Read a key press from LIRC.

        Returns:
            Tuple of (key_name, remote_name, repeat_count) or None
        """
        if not self._socket or not self._connected:
            return None

        try:
            loop = asyncio.get_event_loop()
            data = await asyncio.wait_for(
                loop.run_in_executor(None, self._socket.recv, 256),
                timeout=self._timeout
            )

            if not data:
                return None

            # LIRC format: <code> <repeat> <key_name> <remote_name>
            line = data.decode().strip()
            parts = line.split()

            if len(parts) >= 4:
                code = parts[0]
                repeat = int(parts[1], 16)
                key_name = parts[2]
                remote_name = parts[3]

                return (key_name, remote_name, repeat)

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.debug(f"Error reading LIRC: {e}")
            return None

        return None


class IRRemoteService:
    """
    IR Remote Control Service for Croom UI.

    Manages IR input, key mapping, and action dispatch.
    """

    def __init__(
        self,
        lirc_socket: str = "/var/run/lirc/lircd",
        keymap: Optional[IRKeymap] = None
    ):
        self._lirc = LIRCClient(lirc_socket)
        self._keymap = keymap or SAMSUNG_KEYMAP
        self._custom_keymaps: Dict[str, IRKeymap] = {}
        self._running = False
        self._listeners: Dict[IRAction, List[Callable]] = {}
        self._last_key: Optional[str] = None
        self._last_key_time: float = 0
        self._repeat_count: int = 0

    async def start(self) -> bool:
        """Start the IR remote service."""
        if self._running:
            return True

        if not await self._lirc.connect():
            logger.warning("IR remote service not available (LIRC not running)")
            return False

        self._running = True
        asyncio.create_task(self._read_loop())

        logger.info(f"IR remote service started with keymap: {self._keymap.name}")
        return True

    async def stop(self) -> None:
        """Stop the IR remote service."""
        self._running = False
        await self._lirc.disconnect()
        logger.info("IR remote service stopped")

    def set_keymap(self, keymap: IRKeymap) -> None:
        """Set the active keymap."""
        self._keymap = keymap
        logger.info(f"Keymap changed to: {keymap.name}")

    def set_keymap_by_name(self, name: str) -> bool:
        """Set keymap by name from built-in or custom keymaps."""
        if name in BUILTIN_KEYMAPS:
            self._keymap = BUILTIN_KEYMAPS[name]
            return True
        elif name in self._custom_keymaps:
            self._keymap = self._custom_keymaps[name]
            return True
        return False

    def add_custom_keymap(self, keymap: IRKeymap) -> None:
        """Add a custom keymap."""
        self._custom_keymaps[keymap.remote_type] = keymap

    def load_keymap_from_file(self, path: str) -> Optional[IRKeymap]:
        """Load keymap from JSON configuration file."""
        import json

        try:
            with open(path) as f:
                data = json.load(f)

            mappings = {
                k: IRAction(v) for k, v in data.get("mappings", {}).items()
            }

            keymap = IRKeymap(
                name=data.get("name", "Custom"),
                remote_type=data.get("remote_type", "custom"),
                mappings=mappings,
                repeat_delay=data.get("repeat_delay", 200),
                repeat_rate=data.get("repeat_rate", 100),
            )

            self._custom_keymaps[keymap.remote_type] = keymap
            logger.info(f"Loaded custom keymap: {keymap.name}")
            return keymap

        except Exception as e:
            logger.error(f"Failed to load keymap from {path}: {e}")
            return None

    def add_listener(
        self,
        action: IRAction,
        callback: Callable[[IRAction, int], None]
    ) -> None:
        """
        Add listener for an IR action.

        Args:
            action: The IR action to listen for
            callback: Function called with (action, repeat_count)
        """
        if action not in self._listeners:
            self._listeners[action] = []
        self._listeners[action].append(callback)

    def remove_listener(
        self,
        action: IRAction,
        callback: Callable[[IRAction, int], None]
    ) -> None:
        """Remove a listener."""
        if action in self._listeners:
            try:
                self._listeners[action].remove(callback)
            except ValueError:
                pass

    def add_global_listener(
        self,
        callback: Callable[[IRAction, int], None]
    ) -> None:
        """Add listener for all IR actions."""
        for action in IRAction:
            self.add_listener(action, callback)

    async def _read_loop(self) -> None:
        """Main loop for reading IR input."""
        while self._running:
            try:
                result = await self._lirc.read_key()

                if result:
                    key_name, remote_name, repeat = result
                    await self._handle_key(key_name, repeat)

            except Exception as e:
                logger.error(f"Error in IR read loop: {e}")
                await asyncio.sleep(0.5)

            await asyncio.sleep(0.01)

    async def _handle_key(self, key_name: str, repeat: int) -> None:
        """Handle a key press from LIRC."""
        action = self._keymap.mappings.get(key_name)

        if not action:
            logger.debug(f"Unmapped IR key: {key_name}")
            return

        # Handle key repeat
        import time
        current_time = time.time() * 1000

        if repeat == 0:
            # New key press
            self._last_key = key_name
            self._last_key_time = current_time
            self._repeat_count = 0
        else:
            # Key repeat
            if key_name != self._last_key:
                return

            elapsed = current_time - self._last_key_time

            if self._repeat_count == 0:
                # First repeat - check delay
                if elapsed < self._keymap.repeat_delay:
                    return
            else:
                # Subsequent repeats - check rate
                if elapsed < self._keymap.repeat_rate:
                    return

            self._repeat_count += 1
            self._last_key_time = current_time

        # Dispatch to listeners
        await self._dispatch_action(action, self._repeat_count)

    async def _dispatch_action(self, action: IRAction, repeat: int) -> None:
        """Dispatch action to listeners."""
        if action in self._listeners:
            for callback in self._listeners[action]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(action, repeat)
                    else:
                        callback(action, repeat)
                except Exception as e:
                    logger.error(f"Error in IR listener callback: {e}")


class IRNavigationHandler:
    """
    Handles IR remote navigation for QML UI.

    Bridges IR actions to UI focus navigation and controls.
    """

    def __init__(self, ir_service: IRRemoteService):
        self._ir_service = ir_service
        self._qml_bridge = None
        self._enabled = True

        # Register navigation handlers
        self._ir_service.add_listener(IRAction.UP, self._on_up)
        self._ir_service.add_listener(IRAction.DOWN, self._on_down)
        self._ir_service.add_listener(IRAction.LEFT, self._on_left)
        self._ir_service.add_listener(IRAction.RIGHT, self._on_right)
        self._ir_service.add_listener(IRAction.OK, self._on_ok)
        self._ir_service.add_listener(IRAction.BACK, self._on_back)
        self._ir_service.add_listener(IRAction.HOME, self._on_home)

        # Volume controls
        self._ir_service.add_listener(IRAction.VOLUME_UP, self._on_volume_up)
        self._ir_service.add_listener(IRAction.VOLUME_DOWN, self._on_volume_down)
        self._ir_service.add_listener(IRAction.MUTE, self._on_mute)

        # Number keys
        for i in range(10):
            action = getattr(IRAction, f"NUM_{i}")
            self._ir_service.add_listener(action, self._on_number)

    def set_qml_bridge(self, bridge) -> None:
        """Set QML bridge for sending events."""
        self._qml_bridge = bridge

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable IR navigation."""
        self._enabled = enabled

    def _send_to_qml(self, event: str, data: Dict[str, Any] = None) -> None:
        """Send event to QML."""
        if self._qml_bridge and self._enabled:
            self._qml_bridge.send_ir_event(event, data or {})

    def _on_up(self, action: IRAction, repeat: int) -> None:
        self._send_to_qml("navigate", {"direction": "up"})

    def _on_down(self, action: IRAction, repeat: int) -> None:
        self._send_to_qml("navigate", {"direction": "down"})

    def _on_left(self, action: IRAction, repeat: int) -> None:
        self._send_to_qml("navigate", {"direction": "left"})

    def _on_right(self, action: IRAction, repeat: int) -> None:
        self._send_to_qml("navigate", {"direction": "right"})

    def _on_ok(self, action: IRAction, repeat: int) -> None:
        if repeat == 0:  # Only on first press, not repeat
            self._send_to_qml("select", {})

    def _on_back(self, action: IRAction, repeat: int) -> None:
        if repeat == 0:
            self._send_to_qml("back", {})

    def _on_home(self, action: IRAction, repeat: int) -> None:
        if repeat == 0:
            self._send_to_qml("home", {})

    def _on_volume_up(self, action: IRAction, repeat: int) -> None:
        self._send_to_qml("volume", {"direction": "up"})

    def _on_volume_down(self, action: IRAction, repeat: int) -> None:
        self._send_to_qml("volume", {"direction": "down"})

    def _on_mute(self, action: IRAction, repeat: int) -> None:
        if repeat == 0:
            self._send_to_qml("mute", {})

    def _on_number(self, action: IRAction, repeat: int) -> None:
        if repeat == 0:
            number = int(action.value.split("_")[1])
            self._send_to_qml("number", {"digit": number})


class IRMeetingController:
    """
    Handles IR remote meeting controls.

    Maps IR actions to meeting control functions.
    """

    def __init__(self, ir_service: IRRemoteService):
        self._ir_service = ir_service
        self._meeting_service = None
        self._enabled = True

        # Register meeting control handlers
        self._ir_service.add_listener(IRAction.TOGGLE_MIC, self._on_toggle_mic)
        self._ir_service.add_listener(IRAction.TOGGLE_CAMERA, self._on_toggle_camera)
        self._ir_service.add_listener(IRAction.LEAVE_MEETING, self._on_leave_meeting)
        self._ir_service.add_listener(IRAction.RAISE_HAND, self._on_raise_hand)
        self._ir_service.add_listener(IRAction.SHARE_SCREEN, self._on_share_screen)

        # Color button mappings for quick actions
        self._ir_service.add_listener(IRAction.RED, self._on_toggle_mic)    # Red = mute
        self._ir_service.add_listener(IRAction.GREEN, self._on_toggle_camera)  # Green = camera
        self._ir_service.add_listener(IRAction.YELLOW, self._on_raise_hand)   # Yellow = hand
        self._ir_service.add_listener(IRAction.BLUE, self._on_share_screen)   # Blue = share

    def set_meeting_service(self, meeting_service) -> None:
        """Set meeting service for control."""
        self._meeting_service = meeting_service

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable meeting controls."""
        self._enabled = enabled

    async def _on_toggle_mic(self, action: IRAction, repeat: int) -> None:
        if repeat == 0 and self._enabled and self._meeting_service:
            await self._meeting_service.toggle_mute()
            logger.info("IR: Toggled microphone")

    async def _on_toggle_camera(self, action: IRAction, repeat: int) -> None:
        if repeat == 0 and self._enabled and self._meeting_service:
            await self._meeting_service.toggle_camera()
            logger.info("IR: Toggled camera")

    async def _on_leave_meeting(self, action: IRAction, repeat: int) -> None:
        if repeat == 0 and self._enabled and self._meeting_service:
            await self._meeting_service.leave_meeting()
            logger.info("IR: Left meeting")

    async def _on_raise_hand(self, action: IRAction, repeat: int) -> None:
        if repeat == 0 and self._enabled and self._meeting_service:
            await self._meeting_service.raise_hand()
            logger.info("IR: Raised hand")

    async def _on_share_screen(self, action: IRAction, repeat: int) -> None:
        if repeat == 0 and self._enabled and self._meeting_service:
            await self._meeting_service.toggle_screen_share()
            logger.info("IR: Toggled screen share")
