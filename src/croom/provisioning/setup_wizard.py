"""
Setup wizard web server for Croom provisioning.

Provides a mobile-friendly web interface for device configuration.
"""

import asyncio
import logging
import json
import qrcode
import io
import base64
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Check for aiohttp
try:
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


@dataclass
class WizardConfig:
    """Setup wizard configuration."""
    host: str = "0.0.0.0"
    port: int = 8080
    timeout: int = 1800  # 30 minutes


class SetupWizard:
    """
    Web-based setup wizard for device provisioning.

    Serves a mobile-friendly interface for:
    - WiFi configuration
    - Meeting platform setup
    - Room configuration
    - Dashboard registration
    """

    def __init__(self, config: Optional[WizardConfig] = None):
        self.config = config or WizardConfig()
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._running = False

        # Callbacks
        self._on_wifi_configured: Optional[Callable] = None
        self._on_setup_complete: Optional[Callable] = None

        # State
        self._wifi_networks: List[Dict] = []
        self._setup_data: Dict[str, Any] = {}

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> bool:
        """Start the setup wizard web server."""
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp not installed: pip install aiohttp")
            return False

        if self._running:
            return True

        try:
            # Create application
            self._app = web.Application()
            self._setup_routes()

            # Start server
            self._runner = web.AppRunner(self._app)
            await self._runner.setup()

            self._site = web.TCPSite(
                self._runner,
                self.config.host,
                self.config.port,
            )
            await self._site.start()

            self._running = True
            logger.info(f"Setup wizard started on http://{self.config.host}:{self.config.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start setup wizard: {e}")
            return False

    async def stop(self) -> None:
        """Stop the setup wizard web server."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

        self._app = None
        self._site = None
        self._running = False
        logger.info("Setup wizard stopped")

    def _setup_routes(self) -> None:
        """Configure web routes."""
        self._app.router.add_get('/', self._handle_index)
        self._app.router.add_get('/setup', self._handle_setup)
        self._app.router.add_get('/api/wifi/networks', self._handle_wifi_scan)
        self._app.router.add_post('/api/wifi/connect', self._handle_wifi_connect)
        self._app.router.add_post('/api/setup/complete', self._handle_setup_complete)
        self._app.router.add_get('/api/qrcode', self._handle_qrcode)
        self._app.router.add_get('/api/status', self._handle_status)

    async def _handle_index(self, request: web.Request) -> web.Response:
        """Redirect to setup wizard."""
        raise web.HTTPFound('/setup')

    async def _handle_setup(self, request: web.Request) -> web.Response:
        """Serve the setup wizard HTML."""
        html = self._generate_wizard_html()
        return web.Response(text=html, content_type='text/html')

    async def _handle_wifi_scan(self, request: web.Request) -> web.Response:
        """Return list of WiFi networks."""
        return web.json_response({
            "networks": self._wifi_networks,
        })

    async def _handle_wifi_connect(self, request: web.Request) -> web.Response:
        """Handle WiFi connection request."""
        try:
            data = await request.json()
            ssid = data.get('ssid')
            password = data.get('password')
            hidden = data.get('hidden', False)

            if not ssid:
                return web.json_response(
                    {"error": "SSID required"},
                    status=400
                )

            # Store for callback
            self._setup_data['wifi'] = {
                'ssid': ssid,
                'password': password,
                'hidden': hidden,
            }

            if self._on_wifi_configured:
                success = await self._on_wifi_configured(self._setup_data['wifi'])
                if not success:
                    return web.json_response(
                        {"error": "Failed to connect to WiFi"},
                        status=500
                    )

            return web.json_response({"success": True})

        except Exception as e:
            logger.error(f"WiFi connect error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_setup_complete(self, request: web.Request) -> web.Response:
        """Handle setup completion."""
        try:
            data = await request.json()

            # Validate required fields
            required = ['device_name', 'platform']
            for field in required:
                if field not in data:
                    return web.json_response(
                        {"error": f"{field} is required"},
                        status=400
                    )

            # Store setup data
            self._setup_data.update({
                'device': {
                    'name': data.get('device_name'),
                    'location': data.get('location', ''),
                    'timezone': data.get('timezone', 'UTC'),
                },
                'meeting': {
                    'platform': data.get('platform'),
                    'email': data.get('email'),
                    'password': data.get('password'),
                },
                'dashboard': {
                    'url': data.get('dashboard_url'),
                    'enrollment_token': data.get('enrollment_token'),
                },
            })

            if self._on_setup_complete:
                await self._on_setup_complete(self._setup_data)

            return web.json_response({
                "success": True,
                "message": "Setup complete. Device will restart.",
            })

        except Exception as e:
            logger.error(f"Setup complete error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_qrcode(self, request: web.Request) -> web.Response:
        """Generate QR code for mobile setup."""
        try:
            setup_url = f"http://{self.config.host}:{self.config.port}/setup"

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(setup_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode()

            return web.json_response({
                "qr_code": f"data:image/png;base64,{img_base64}",
                "setup_url": setup_url,
            })

        except Exception as e:
            logger.error(f"QR code generation error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_status(self, request: web.Request) -> web.Response:
        """Return current setup status."""
        return web.json_response({
            "wifi_configured": 'wifi' in self._setup_data,
            "setup_complete": 'device' in self._setup_data,
        })

    def set_wifi_networks(self, networks: List[Dict]) -> None:
        """Set available WiFi networks for display."""
        self._wifi_networks = networks

    def on_wifi_configured(self, callback: Callable) -> None:
        """Register callback for WiFi configuration."""
        self._on_wifi_configured = callback

    def on_setup_complete(self, callback: Callable) -> None:
        """Register callback for setup completion."""
        self._on_setup_complete = callback

    def _generate_wizard_html(self) -> str:
        """Generate the setup wizard HTML."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Croom Setup</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 420px;
            width: 100%;
            overflow: hidden;
        }
        .header {
            background: #4f46e5;
            color: white;
            padding: 24px;
            text-align: center;
        }
        .header h1 { font-size: 24px; margin-bottom: 8px; }
        .header p { opacity: 0.9; font-size: 14px; }
        .content { padding: 24px; }
        .step { display: none; }
        .step.active { display: block; }
        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #374151;
        }
        input, select {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #4f46e5;
        }
        .network-list {
            max-height: 200px;
            overflow-y: auto;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
        }
        .network-item {
            padding: 12px 16px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #f3f4f6;
        }
        .network-item:hover { background: #f9fafb; }
        .network-item.selected { background: #eef2ff; }
        .signal-bars { font-size: 12px; color: #6b7280; }
        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #4f46e5;
            color: white;
        }
        .btn-primary:hover { background: #4338ca; }
        .btn-secondary {
            background: #f3f4f6;
            color: #374151;
            margin-top: 10px;
        }
        .error { color: #dc2626; font-size: 14px; margin-top: 8px; }
        .success {
            text-align: center;
            padding: 40px 20px;
        }
        .success-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #fff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .steps-indicator {
            display: flex;
            justify-content: center;
            padding: 16px;
            background: #f9fafb;
        }
        .step-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #d1d5db;
            margin: 0 6px;
        }
        .step-dot.active { background: #4f46e5; }
        .step-dot.completed { background: #10b981; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Croom Setup</h1>
            <p>Configure your conference room device</p>
        </div>

        <div class="steps-indicator">
            <div class="step-dot active" data-step="1"></div>
            <div class="step-dot" data-step="2"></div>
            <div class="step-dot" data-step="3"></div>
            <div class="step-dot" data-step="4"></div>
        </div>

        <div class="content">
            <!-- Step 1: WiFi -->
            <div class="step active" id="step1">
                <h2 style="margin-bottom: 16px;">Select WiFi Network</h2>
                <div class="network-list" id="networkList">
                    <div style="padding: 20px; text-align: center; color: #6b7280;">
                        Scanning for networks...
                    </div>
                </div>
                <div class="form-group" style="margin-top: 16px;">
                    <input type="password" id="wifiPassword" placeholder="WiFi Password">
                </div>
                <div class="error" id="wifiError"></div>
                <button class="btn btn-primary" onclick="connectWifi()">Connect</button>
                <button class="btn btn-secondary" onclick="useEthernet()">Use Ethernet Instead</button>
            </div>

            <!-- Step 2: Platform -->
            <div class="step" id="step2">
                <h2 style="margin-bottom: 16px;">Meeting Platform</h2>
                <div class="form-group">
                    <label>Platform</label>
                    <select id="platform">
                        <option value="google_meet">Google Meet</option>
                        <option value="teams">Microsoft Teams</option>
                        <option value="zoom">Zoom</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" id="email" placeholder="room@company.com">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="password">
                </div>
                <button class="btn btn-primary" onclick="nextStep(3)">Next</button>
                <button class="btn btn-secondary" onclick="prevStep(1)">Back</button>
            </div>

            <!-- Step 3: Room -->
            <div class="step" id="step3">
                <h2 style="margin-bottom: 16px;">Room Configuration</h2>
                <div class="form-group">
                    <label>Room Name</label>
                    <input type="text" id="deviceName" placeholder="Conference Room A">
                </div>
                <div class="form-group">
                    <label>Location</label>
                    <input type="text" id="location" placeholder="Building 1, Floor 2">
                </div>
                <div class="form-group">
                    <label>Dashboard URL (optional)</label>
                    <input type="url" id="dashboardUrl" placeholder="https://croom.company.com">
                </div>
                <button class="btn btn-primary" onclick="completeSetup()">Finish Setup</button>
                <button class="btn btn-secondary" onclick="prevStep(2)">Back</button>
            </div>

            <!-- Step 4: Complete -->
            <div class="step" id="step4">
                <div class="success">
                    <div class="success-icon">✅</div>
                    <h2>Setup Complete!</h2>
                    <p style="margin-top: 16px; color: #6b7280;">
                        Your Croom device is configured.<br>
                        The device will restart automatically.
                    </p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedNetwork = null;
        let currentStep = 1;

        // Load WiFi networks
        async function loadNetworks() {
            try {
                const response = await fetch('/api/wifi/networks');
                const data = await response.json();
                renderNetworks(data.networks);
            } catch (e) {
                document.getElementById('networkList').innerHTML =
                    '<div style="padding: 20px; text-align: center; color: #dc2626;">Failed to scan networks</div>';
            }
        }

        function renderNetworks(networks) {
            const list = document.getElementById('networkList');
            if (!networks || networks.length === 0) {
                list.innerHTML = '<div style="padding: 20px; text-align: center;">No networks found</div>';
                return;
            }
            list.innerHTML = networks.map(n => `
                <div class="network-item" onclick="selectNetwork('${n.ssid}', this)">
                    <span>${n.ssid}</span>
                    <span class="signal-bars">${getSignalBars(n.signal_strength)}</span>
                </div>
            `).join('');
        }

        function getSignalBars(strength) {
            const bars = Math.ceil(strength / 25);
            return '▂▄▆█'.slice(0, bars);
        }

        function selectNetwork(ssid, element) {
            document.querySelectorAll('.network-item').forEach(el => el.classList.remove('selected'));
            element.classList.add('selected');
            selectedNetwork = ssid;
        }

        async function connectWifi() {
            if (!selectedNetwork) {
                document.getElementById('wifiError').textContent = 'Please select a network';
                return;
            }

            const password = document.getElementById('wifiPassword').value;

            try {
                const response = await fetch('/api/wifi/connect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ssid: selectedNetwork,
                        password: password
                    })
                });

                const data = await response.json();
                if (data.success) {
                    nextStep(2);
                } else {
                    document.getElementById('wifiError').textContent = data.error || 'Connection failed';
                }
            } catch (e) {
                document.getElementById('wifiError').textContent = 'Connection failed';
            }
        }

        function useEthernet() {
            nextStep(2);
        }

        async function completeSetup() {
            const data = {
                device_name: document.getElementById('deviceName').value,
                location: document.getElementById('location').value,
                platform: document.getElementById('platform').value,
                email: document.getElementById('email').value,
                password: document.getElementById('password').value,
                dashboard_url: document.getElementById('dashboardUrl').value
            };

            if (!data.device_name) {
                alert('Please enter a room name');
                return;
            }

            try {
                const response = await fetch('/api/setup/complete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                if (result.success) {
                    nextStep(4);
                } else {
                    alert(result.error || 'Setup failed');
                }
            } catch (e) {
                alert('Setup failed: ' + e.message);
            }
        }

        function nextStep(step) {
            document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
            document.getElementById('step' + step).classList.add('active');

            document.querySelectorAll('.step-dot').forEach((el, i) => {
                el.classList.remove('active', 'completed');
                if (i + 1 < step) el.classList.add('completed');
                if (i + 1 === step) el.classList.add('active');
            });

            currentStep = step;
        }

        function prevStep(step) {
            nextStep(step);
        }

        // Initialize
        loadNetworks();
    </script>
</body>
</html>'''
