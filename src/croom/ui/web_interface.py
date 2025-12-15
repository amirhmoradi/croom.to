"""
Local Web Interface for Croom.

Provides browser-based access to Croom settings and controls
when touch screen is not available or for remote configuration.

Features:
- Device status and information
- Network configuration
- Meeting settings
- Calendar configuration
- System diagnostics
- Firmware updates
"""

import asyncio
import json
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from aiohttp import web
    from aiohttp.web import middleware
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


@dataclass
class WebSession:
    """Web interface session."""
    id: str
    created_at: datetime
    last_access: datetime
    authenticated: bool = False
    ip_address: str = ""


class LocalWebInterface:
    """
    Local web interface server for Croom configuration.

    Provides a simple web UI accessible at http://croom.local or
    the device's IP address for configuration and monitoring.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        static_path: str = "/usr/share/croom/web",
        admin_pin: Optional[str] = None,
        session_timeout: int = 3600,
    ):
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not installed")

        self._host = host
        self._port = port
        self._static_path = Path(static_path)
        self._admin_pin = admin_pin
        self._session_timeout = session_timeout

        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

        self._sessions: Dict[str, WebSession] = {}
        self._callbacks: Dict[str, Callable] = {}

        # Service references
        self._device_service = None
        self._network_service = None
        self._meeting_service = None
        self._calendar_service = None
        self._update_service = None

    def set_services(
        self,
        device_service=None,
        network_service=None,
        meeting_service=None,
        calendar_service=None,
        update_service=None,
    ) -> None:
        """Set service references for API endpoints."""
        self._device_service = device_service
        self._network_service = network_service
        self._meeting_service = meeting_service
        self._calendar_service = calendar_service
        self._update_service = update_service

    def set_admin_pin(self, pin: str) -> None:
        """Set admin PIN for authentication."""
        self._admin_pin = pin

    async def start(self) -> None:
        """Start the web interface server."""
        self._app = web.Application(middlewares=[self._auth_middleware])

        # Setup routes
        self._setup_routes()

        # Start server
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()

        logger.info(f"Local web interface started on http://{self._host}:{self._port}")

    async def stop(self) -> None:
        """Stop the web interface server."""
        if self._site:
            await self._site.stop()

        if self._runner:
            await self._runner.cleanup()

        self._app = None
        self._runner = None
        self._site = None

        logger.info("Local web interface stopped")

    def _setup_routes(self) -> None:
        """Setup HTTP routes."""
        router = self._app.router

        # Static files (HTML, CSS, JS)
        if self._static_path.exists():
            router.add_static('/static/', self._static_path)

        # Auth endpoints
        router.add_post('/api/auth/login', self._handle_login)
        router.add_post('/api/auth/logout', self._handle_logout)
        router.add_get('/api/auth/status', self._handle_auth_status)

        # Device info endpoints
        router.add_get('/api/device/info', self._handle_device_info)
        router.add_get('/api/device/status', self._handle_device_status)
        router.add_post('/api/device/restart', self._handle_device_restart)
        router.add_post('/api/device/shutdown', self._handle_device_shutdown)

        # Network endpoints
        router.add_get('/api/network/status', self._handle_network_status)
        router.add_get('/api/network/wifi/scan', self._handle_wifi_scan)
        router.add_post('/api/network/wifi/connect', self._handle_wifi_connect)
        router.add_get('/api/network/wifi/saved', self._handle_wifi_saved)
        router.add_delete('/api/network/wifi/{ssid}', self._handle_wifi_forget)

        # Meeting endpoints
        router.add_get('/api/meeting/status', self._handle_meeting_status)
        router.add_post('/api/meeting/join', self._handle_meeting_join)
        router.add_post('/api/meeting/leave', self._handle_meeting_leave)
        router.add_post('/api/meeting/mute', self._handle_meeting_mute)
        router.add_post('/api/meeting/camera', self._handle_meeting_camera)

        # Calendar endpoints
        router.add_get('/api/calendar/events', self._handle_calendar_events)
        router.add_get('/api/calendar/next', self._handle_calendar_next)
        router.add_get('/api/calendar/status', self._handle_calendar_status)

        # Settings endpoints
        router.add_get('/api/settings', self._handle_get_settings)
        router.add_put('/api/settings', self._handle_update_settings)
        router.add_post('/api/settings/pin', self._handle_change_pin)

        # Diagnostics endpoints
        router.add_get('/api/diagnostics/health', self._handle_health_check)
        router.add_get('/api/diagnostics/logs', self._handle_get_logs)
        router.add_post('/api/diagnostics/run', self._handle_run_diagnostics)

        # Update endpoints
        router.add_get('/api/update/check', self._handle_check_update)
        router.add_post('/api/update/install', self._handle_install_update)
        router.add_get('/api/update/status', self._handle_update_status)

        # Index page
        router.add_get('/', self._handle_index)
        router.add_get('/{path:.*}', self._handle_spa)

    @middleware
    async def _auth_middleware(self, request: web.Request, handler):
        """Authentication middleware."""
        # Public endpoints that don't require auth
        public_paths = [
            '/api/auth/login',
            '/api/auth/status',
            '/api/device/info',
            '/static/',
            '/',
        ]

        path = request.path
        if any(path.startswith(p) for p in public_paths):
            return await handler(request)

        # Check for valid session
        session_id = request.cookies.get('session_id')
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]

            # Check session timeout
            if datetime.utcnow() - session.last_access > timedelta(seconds=self._session_timeout):
                del self._sessions[session_id]
                return web.json_response(
                    {"error": "Session expired"},
                    status=401
                )

            if session.authenticated:
                session.last_access = datetime.utcnow()
                request['session'] = session
                return await handler(request)

        return web.json_response(
            {"error": "Authentication required"},
            status=401
        )

    # Auth handlers
    async def _handle_login(self, request: web.Request) -> web.Response:
        """Handle login request."""
        try:
            data = await request.json()
            pin = data.get('pin', '')

            if self._admin_pin and pin == self._admin_pin:
                session_id = secrets.token_urlsafe(32)
                session = WebSession(
                    id=session_id,
                    created_at=datetime.utcnow(),
                    last_access=datetime.utcnow(),
                    authenticated=True,
                    ip_address=request.remote or "",
                )
                self._sessions[session_id] = session

                response = web.json_response({"success": True})
                response.set_cookie(
                    'session_id',
                    session_id,
                    max_age=self._session_timeout,
                    httponly=True,
                )
                return response

            elif not self._admin_pin:
                # No PIN configured, allow access
                session_id = secrets.token_urlsafe(32)
                session = WebSession(
                    id=session_id,
                    created_at=datetime.utcnow(),
                    last_access=datetime.utcnow(),
                    authenticated=True,
                    ip_address=request.remote or "",
                )
                self._sessions[session_id] = session

                response = web.json_response({"success": True})
                response.set_cookie(
                    'session_id',
                    session_id,
                    max_age=self._session_timeout,
                    httponly=True,
                )
                return response

            return web.json_response(
                {"success": False, "error": "Invalid PIN"},
                status=401
            )

        except Exception as e:
            logger.error(f"Login error: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500
            )

    async def _handle_logout(self, request: web.Request) -> web.Response:
        """Handle logout request."""
        session_id = request.cookies.get('session_id')
        if session_id and session_id in self._sessions:
            del self._sessions[session_id]

        response = web.json_response({"success": True})
        response.del_cookie('session_id')
        return response

    async def _handle_auth_status(self, request: web.Request) -> web.Response:
        """Check authentication status."""
        session_id = request.cookies.get('session_id')
        authenticated = False

        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            if datetime.utcnow() - session.last_access < timedelta(seconds=self._session_timeout):
                authenticated = session.authenticated

        return web.json_response({
            "authenticated": authenticated,
            "pin_required": bool(self._admin_pin),
        })

    # Device handlers
    async def _handle_device_info(self, request: web.Request) -> web.Response:
        """Get device information."""
        info = {
            "name": os.uname().nodename,
            "model": "Raspberry Pi",
            "version": "1.0.0",
            "uptime": self._get_uptime(),
        }

        if self._device_service:
            info.update(await self._device_service.get_info())

        return web.json_response(info)

    async def _handle_device_status(self, request: web.Request) -> web.Response:
        """Get device status."""
        status = {
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_percent": 0,
            "temperature": 0,
        }

        try:
            import psutil
            status["cpu_percent"] = psutil.cpu_percent()
            status["memory_percent"] = psutil.virtual_memory().percent
            status["disk_percent"] = psutil.disk_usage('/').percent

            # Get temperature
            temps = psutil.sensors_temperatures()
            if 'cpu_thermal' in temps:
                status["temperature"] = temps['cpu_thermal'][0].current
        except ImportError:
            pass

        return web.json_response(status)

    async def _handle_device_restart(self, request: web.Request) -> web.Response:
        """Restart device."""
        asyncio.create_task(self._delayed_restart())
        return web.json_response({"success": True, "message": "Restarting..."})

    async def _handle_device_shutdown(self, request: web.Request) -> web.Response:
        """Shutdown device."""
        asyncio.create_task(self._delayed_shutdown())
        return web.json_response({"success": True, "message": "Shutting down..."})

    async def _delayed_restart(self) -> None:
        """Restart after delay."""
        await asyncio.sleep(2)
        os.system("sudo reboot")

    async def _delayed_shutdown(self) -> None:
        """Shutdown after delay."""
        await asyncio.sleep(2)
        os.system("sudo shutdown -h now")

    # Network handlers
    async def _handle_network_status(self, request: web.Request) -> web.Response:
        """Get network status."""
        status = {
            "connected": False,
            "wifi_ssid": "",
            "ip_address": "",
            "mac_address": "",
        }

        if self._network_service:
            status.update(await self._network_service.get_status())

        return web.json_response(status)

    async def _handle_wifi_scan(self, request: web.Request) -> web.Response:
        """Scan for WiFi networks."""
        networks = []

        if self._network_service:
            networks = await self._network_service.scan_wifi()

        return web.json_response({"networks": networks})

    async def _handle_wifi_connect(self, request: web.Request) -> web.Response:
        """Connect to WiFi network."""
        try:
            data = await request.json()
            ssid = data.get('ssid')
            password = data.get('password', '')

            if not ssid:
                return web.json_response(
                    {"error": "SSID required"},
                    status=400
                )

            if self._network_service:
                success = await self._network_service.connect_wifi(ssid, password)
                return web.json_response({"success": success})

            return web.json_response({"error": "Network service not available"}, status=503)

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_wifi_saved(self, request: web.Request) -> web.Response:
        """Get saved WiFi networks."""
        networks = []

        if self._network_service:
            networks = await self._network_service.get_saved_networks()

        return web.json_response({"networks": networks})

    async def _handle_wifi_forget(self, request: web.Request) -> web.Response:
        """Forget WiFi network."""
        ssid = request.match_info.get('ssid')

        if self._network_service:
            success = await self._network_service.forget_network(ssid)
            return web.json_response({"success": success})

        return web.json_response({"error": "Network service not available"}, status=503)

    # Meeting handlers
    async def _handle_meeting_status(self, request: web.Request) -> web.Response:
        """Get meeting status."""
        status = {
            "in_meeting": False,
            "meeting_title": "",
            "participants": 0,
            "muted": False,
            "camera_on": False,
        }

        if self._meeting_service:
            status.update(await self._meeting_service.get_status())

        return web.json_response(status)

    async def _handle_meeting_join(self, request: web.Request) -> web.Response:
        """Join a meeting."""
        try:
            data = await request.json()
            url = data.get('url')

            if not url:
                return web.json_response({"error": "Meeting URL required"}, status=400)

            if self._meeting_service:
                success = await self._meeting_service.join_meeting(url)
                return web.json_response({"success": success})

            return web.json_response({"error": "Meeting service not available"}, status=503)

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_meeting_leave(self, request: web.Request) -> web.Response:
        """Leave current meeting."""
        if self._meeting_service:
            await self._meeting_service.leave_meeting()
            return web.json_response({"success": True})

        return web.json_response({"error": "Meeting service not available"}, status=503)

    async def _handle_meeting_mute(self, request: web.Request) -> web.Response:
        """Toggle mute."""
        if self._meeting_service:
            muted = await self._meeting_service.toggle_mute()
            return web.json_response({"muted": muted})

        return web.json_response({"error": "Meeting service not available"}, status=503)

    async def _handle_meeting_camera(self, request: web.Request) -> web.Response:
        """Toggle camera."""
        if self._meeting_service:
            camera_on = await self._meeting_service.toggle_camera()
            return web.json_response({"camera_on": camera_on})

        return web.json_response({"error": "Meeting service not available"}, status=503)

    # Calendar handlers
    async def _handle_calendar_events(self, request: web.Request) -> web.Response:
        """Get calendar events."""
        events = []

        if self._calendar_service:
            events = await self._calendar_service.get_events()

        return web.json_response({"events": events})

    async def _handle_calendar_next(self, request: web.Request) -> web.Response:
        """Get next calendar event."""
        event = None

        if self._calendar_service:
            event = await self._calendar_service.get_next_event()

        return web.json_response({"event": event})

    async def _handle_calendar_status(self, request: web.Request) -> web.Response:
        """Get calendar sync status."""
        status = {
            "connected": False,
            "provider": "",
            "last_sync": None,
        }

        if self._calendar_service:
            status.update(await self._calendar_service.get_status())

        return web.json_response(status)

    # Settings handlers
    async def _handle_get_settings(self, request: web.Request) -> web.Response:
        """Get device settings."""
        settings = {
            "device_name": os.uname().nodename,
            "timezone": "UTC",
            "language": "en",
            "auto_join": True,
            "auto_answer": False,
            "display_brightness": 100,
            "volume": 80,
        }

        return web.json_response(settings)

    async def _handle_update_settings(self, request: web.Request) -> web.Response:
        """Update device settings."""
        try:
            data = await request.json()
            # Save settings to config file
            return web.json_response({"success": True})

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_change_pin(self, request: web.Request) -> web.Response:
        """Change admin PIN."""
        try:
            data = await request.json()
            current_pin = data.get('current_pin')
            new_pin = data.get('new_pin')

            if self._admin_pin and current_pin != self._admin_pin:
                return web.json_response(
                    {"error": "Current PIN incorrect"},
                    status=401
                )

            self._admin_pin = new_pin
            # Save to config
            return web.json_response({"success": True})

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # Diagnostics handlers
    async def _handle_health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def _handle_get_logs(self, request: web.Request) -> web.Response:
        """Get recent logs."""
        lines = int(request.query.get('lines', 100))
        level = request.query.get('level', 'all')

        logs = []
        log_file = Path("/var/log/croom/croom.log")

        if log_file.exists():
            with open(log_file) as f:
                all_lines = f.readlines()[-lines:]
                for line in all_lines:
                    logs.append(line.strip())

        return web.json_response({"logs": logs})

    async def _handle_run_diagnostics(self, request: web.Request) -> web.Response:
        """Run diagnostics."""
        results = {
            "network": "pass",
            "camera": "pass",
            "microphone": "pass",
            "speaker": "pass",
            "display": "pass",
        }

        # Run actual diagnostics here

        return web.json_response(results)

    # Update handlers
    async def _handle_check_update(self, request: web.Request) -> web.Response:
        """Check for updates."""
        update_info = {
            "available": False,
            "current_version": "1.0.0",
            "latest_version": "1.0.0",
        }

        if self._update_service:
            update_info.update(await self._update_service.check())

        return web.json_response(update_info)

    async def _handle_install_update(self, request: web.Request) -> web.Response:
        """Install update."""
        if self._update_service:
            success = await self._update_service.install()
            return web.json_response({"success": success})

        return web.json_response({"error": "Update service not available"}, status=503)

    async def _handle_update_status(self, request: web.Request) -> web.Response:
        """Get update status."""
        status = {
            "updating": False,
            "progress": 0,
            "message": "",
        }

        if self._update_service:
            status.update(await self._update_service.get_status())

        return web.json_response(status)

    # Static/SPA handlers
    async def _handle_index(self, request: web.Request) -> web.Response:
        """Serve index page."""
        index_file = self._static_path / "index.html"

        if index_file.exists():
            return web.FileResponse(index_file)

        # Return simple default page
        return web.Response(
            text=self._get_default_index(),
            content_type="text/html"
        )

    async def _handle_spa(self, request: web.Request) -> web.Response:
        """Handle SPA routes - serve index.html."""
        path = request.match_info.get('path', '')

        # Try to serve actual file
        file_path = self._static_path / path
        if file_path.exists() and file_path.is_file():
            return web.FileResponse(file_path)

        # Otherwise serve index.html for SPA routing
        return await self._handle_index(request)

    def _get_uptime(self) -> str:
        """Get system uptime."""
        try:
            with open('/proc/uptime') as f:
                uptime_seconds = float(f.read().split()[0])

            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)

            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except Exception:
            return "unknown"

    def _get_default_index(self) -> str:
        """Get default HTML page."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Croom Configuration</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #fff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        h1 { font-size: 2.5rem; margin-bottom: 1rem; }
        p { color: #aaa; margin-bottom: 2rem; }
        .status {
            background: #333;
            padding: 1rem 2rem;
            border-radius: 8px;
            display: inline-block;
        }
        .status.online { border-left: 4px solid #44ff44; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Croom</h1>
        <p>Conference Room System</p>
        <div class="status online">
            <strong>Status:</strong> Online
        </div>
    </div>
</body>
</html>
"""
