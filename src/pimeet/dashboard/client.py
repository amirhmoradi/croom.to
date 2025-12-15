"""
Dashboard client for PiMeet devices.

Provides WebSocket-based communication with management dashboard.
"""

import asyncio
import json
import logging
import platform
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from enum import Enum

logger = logging.getLogger(__name__)

# Check for websockets library
try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = None


class ConnectionState(Enum):
    """WebSocket connection state."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


class MessageType(Enum):
    """Dashboard message types."""
    # Device -> Dashboard
    REGISTER = "register"
    HEARTBEAT = "heartbeat"
    METRICS = "metrics"
    STATUS = "status"
    EVENT = "event"
    LOG = "log"

    # Dashboard -> Device
    COMMAND = "command"
    CONFIG = "config"
    ACK = "ack"
    ERROR = "error"


class DashboardClient:
    """
    WebSocket client for dashboard communication.

    Handles:
    - Device registration
    - Heartbeat/keepalive
    - Metrics reporting
    - Remote command execution
    - Configuration sync
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize dashboard client.

        Args:
            config: Client configuration with:
                - url: Dashboard WebSocket URL
                - device_id: Unique device identifier
                - api_key: Authentication key
                - room_name: Room display name
                - heartbeat_interval: Seconds between heartbeats (default 30)
                - reconnect_interval: Seconds between reconnect attempts (default 5)
                - max_reconnect_attempts: Max reconnect tries (default 10)
        """
        self.config = config or {}

        # Connection settings
        self._url = self.config.get('url', 'ws://localhost:3001/ws')
        self._device_id = self.config.get('device_id') or self._generate_device_id()
        self._api_key = self.config.get('api_key', '')
        self._room_name = self.config.get('room_name', 'Conference Room')

        # Timing
        self._heartbeat_interval = self.config.get('heartbeat_interval', 30)
        self._reconnect_interval = self.config.get('reconnect_interval', 5)
        self._max_reconnect_attempts = self.config.get('max_reconnect_attempts', 10)

        # State
        self._state = ConnectionState.DISCONNECTED
        self._ws: Optional[WebSocketClientProtocol] = None
        self._running = False
        self._registered = False
        self._reconnect_count = 0

        # Tasks
        self._connection_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None

        # Callbacks
        self._command_handlers: Dict[str, Callable] = {}
        self._on_connected: List[Callable] = []
        self._on_disconnected: List[Callable] = []
        self._on_config_update: List[Callable[[Dict], None]] = []

        # Message queue for offline buffering
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    def _generate_device_id(self) -> str:
        """Generate unique device ID based on hardware."""
        try:
            # Try to get Pi serial
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        serial = line.split(':')[1].strip()
                        return f"pimeet-{serial[-8:]}"
        except Exception:
            pass

        # Fallback to MAC address based
        mac = uuid.getnode()
        return f"pimeet-{mac:012x}"[-16:]

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def device_id(self) -> str:
        """Get device ID."""
        return self._device_id

    @property
    def is_connected(self) -> bool:
        """Whether connected to dashboard."""
        return self._state == ConnectionState.CONNECTED

    async def connect(self) -> bool:
        """
        Connect to the dashboard.

        Returns:
            True if connection established
        """
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets library not installed")
            return False

        if self._running:
            return self.is_connected

        self._running = True
        self._connection_task = asyncio.create_task(self._connection_loop())

        # Wait for initial connection
        for _ in range(50):  # 5 seconds
            if self.is_connected:
                return True
            await asyncio.sleep(0.1)

        return self.is_connected

    async def disconnect(self) -> None:
        """Disconnect from the dashboard."""
        self._running = False

        # Cancel tasks
        for task in [self._heartbeat_task, self._receive_task, self._connection_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close WebSocket
        if self._ws:
            await self._ws.close()
            self._ws = None

        self._state = ConnectionState.DISCONNECTED
        self._registered = False
        logger.info("Disconnected from dashboard")

    async def _connection_loop(self) -> None:
        """Main connection management loop."""
        while self._running:
            try:
                self._state = ConnectionState.CONNECTING
                logger.info(f"Connecting to dashboard: {self._url}")

                async with websockets.connect(
                    self._url,
                    extra_headers={
                        "X-Device-ID": self._device_id,
                        "X-API-Key": self._api_key,
                    },
                    ping_interval=20,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    self._state = ConnectionState.CONNECTED
                    self._reconnect_count = 0

                    logger.info("Connected to dashboard")

                    # Register device
                    await self._register()

                    # Notify listeners
                    for callback in self._on_connected:
                        try:
                            callback()
                        except Exception as e:
                            logger.error(f"Connected callback error: {e}")

                    # Start background tasks
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                    self._receive_task = asyncio.create_task(self._receive_loop())

                    # Send queued messages
                    await self._flush_queue()

                    # Wait for disconnect
                    await asyncio.gather(
                        self._heartbeat_task,
                        self._receive_task,
                        return_exceptions=True,
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection error: {e}")

                self._state = ConnectionState.RECONNECTING
                self._reconnect_count += 1

                # Notify listeners
                for callback in self._on_disconnected:
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"Disconnected callback error: {e}")

                if self._reconnect_count >= self._max_reconnect_attempts:
                    logger.error("Max reconnect attempts reached")
                    break

                logger.info(f"Reconnecting in {self._reconnect_interval}s...")
                await asyncio.sleep(self._reconnect_interval)

        self._state = ConnectionState.DISCONNECTED

    async def _register(self) -> None:
        """Register device with dashboard."""
        import sys

        registration = {
            "type": MessageType.REGISTER.value,
            "device_id": self._device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "name": self._room_name,
                "platform": platform.system(),
                "platform_version": platform.release(),
                "python_version": sys.version.split()[0],
                "hostname": platform.node(),
                "architecture": platform.machine(),
            },
        }

        await self._send(registration)
        self._registered = True
        logger.info(f"Registered device: {self._device_id}")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        while self._running and self.is_connected:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                heartbeat = {
                    "type": MessageType.HEARTBEAT.value,
                    "device_id": self._device_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                await self._send(heartbeat)
                logger.debug("Heartbeat sent")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break

    async def _receive_loop(self) -> None:
        """Receive and handle incoming messages."""
        while self._running and self._ws:
            try:
                message = await self._ws.recv()
                data = json.loads(message)

                msg_type = data.get('type', '')
                logger.debug(f"Received: {msg_type}")

                await self._handle_message(data)

            except asyncio.CancelledError:
                break
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed by server")
                break
            except Exception as e:
                logger.error(f"Receive error: {e}")
                break

    async def _handle_message(self, data: Dict) -> None:
        """Handle incoming message."""
        msg_type = data.get('type', '')

        if msg_type == MessageType.COMMAND.value:
            command = data.get('command', '')
            params = data.get('params', {})

            # Execute command handler
            handler = self._command_handlers.get(command)
            if handler:
                try:
                    result = await handler(params) if asyncio.iscoroutinefunction(handler) else handler(params)

                    # Send response
                    await self._send({
                        "type": MessageType.ACK.value,
                        "device_id": self._device_id,
                        "command_id": data.get('command_id'),
                        "result": result,
                    })

                except Exception as e:
                    logger.error(f"Command error: {e}")
                    await self._send({
                        "type": MessageType.ERROR.value,
                        "device_id": self._device_id,
                        "command_id": data.get('command_id'),
                        "error": str(e),
                    })
            else:
                logger.warning(f"Unknown command: {command}")

        elif msg_type == MessageType.CONFIG.value:
            config = data.get('config', {})
            for callback in self._on_config_update:
                try:
                    callback(config)
                except Exception as e:
                    logger.error(f"Config callback error: {e}")

        elif msg_type == MessageType.ACK.value:
            logger.debug(f"Received ACK for: {data.get('message_id')}")

    async def _send(self, message: Dict) -> bool:
        """Send message to dashboard."""
        if not self._ws or not self.is_connected:
            # Queue for later
            try:
                self._message_queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Message queue full, dropping message")
            return False

        try:
            await self._ws.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False

    async def _flush_queue(self) -> None:
        """Send all queued messages."""
        while not self._message_queue.empty():
            try:
                message = self._message_queue.get_nowait()
                await self._send(message)
            except asyncio.QueueEmpty:
                break

    # Public API

    async def send_metrics(self, metrics: Dict[str, Any]) -> bool:
        """
        Send metrics to dashboard.

        Args:
            metrics: Metrics data dictionary

        Returns:
            True if sent successfully
        """
        message = {
            "type": MessageType.METRICS.value,
            "device_id": self._device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": metrics,
        }
        return await self._send(message)

    async def send_status(self, status: str, details: Optional[Dict] = None) -> bool:
        """
        Send status update to dashboard.

        Args:
            status: Status string (e.g., 'idle', 'in_meeting', 'error')
            details: Additional status details

        Returns:
            True if sent successfully
        """
        message = {
            "type": MessageType.STATUS.value,
            "device_id": self._device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "details": details or {},
        }
        return await self._send(message)

    async def send_event(self, event_type: str, data: Optional[Dict] = None) -> bool:
        """
        Send event to dashboard.

        Args:
            event_type: Event type (e.g., 'meeting_started', 'person_detected')
            data: Event data

        Returns:
            True if sent successfully
        """
        message = {
            "type": MessageType.EVENT.value,
            "device_id": self._device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "data": data or {},
        }
        return await self._send(message)

    async def send_log(self, level: str, message_text: str, extra: Optional[Dict] = None) -> bool:
        """
        Send log entry to dashboard.

        Args:
            level: Log level (debug, info, warning, error)
            message_text: Log message
            extra: Additional data

        Returns:
            True if sent successfully
        """
        message = {
            "type": MessageType.LOG.value,
            "device_id": self._device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message_text,
            "extra": extra or {},
        }
        return await self._send(message)

    def register_command(self, command: str, handler: Callable) -> None:
        """
        Register a command handler.

        Args:
            command: Command name
            handler: Handler function (can be async)
        """
        self._command_handlers[command] = handler
        logger.debug(f"Registered command handler: {command}")

    def on_connected(self, callback: Callable) -> None:
        """Register callback for connection established."""
        self._on_connected.append(callback)

    def on_disconnected(self, callback: Callable) -> None:
        """Register callback for connection lost."""
        self._on_disconnected.append(callback)

    def on_config_update(self, callback: Callable[[Dict], None]) -> None:
        """Register callback for configuration updates."""
        self._on_config_update.append(callback)


def create_dashboard_client(config: Dict[str, Any]) -> DashboardClient:
    """
    Create a dashboard client from configuration.

    Args:
        config: Dashboard client configuration

    Returns:
        Configured DashboardClient instance
    """
    return DashboardClient(config)
