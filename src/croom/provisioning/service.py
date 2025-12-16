"""
Provisioning service for Croom.

Orchestrates the device provisioning process.
"""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

from croom.provisioning.captive_portal import CaptivePortal, APConfig
from croom.provisioning.usb_config import USBConfigReader, DeviceConfig
from croom.provisioning.setup_wizard import SetupWizard, WizardConfig
from croom.provisioning.network import NetworkManager, WiFiConfig, WiFiSecurity
from croom.provisioning.enrollment import DashboardEnrollment, EnrollmentStatus
from croom.security.encryption import EncryptionService, create_key_storage

logger = logging.getLogger(__name__)


class ProvisioningState(Enum):
    """Device provisioning state."""
    CHECKING = "checking"
    USB_CONFIG = "usb_config"
    SETUP_MODE = "setup_mode"
    ENROLLING = "enrolling"
    CONFIGURED = "configured"
    ERROR = "error"


@dataclass
class ProvisioningConfig:
    """Provisioning service configuration."""
    config_path: str = "/etc/croom"
    setup_timeout: int = 1800  # 30 minutes
    ap_ssid_prefix: str = "Croom-Setup"
    wizard_port: int = 8080
    auto_enroll: bool = True


class ProvisioningService:
    """
    Main provisioning service.

    Handles the complete device provisioning workflow:
    1. Check for existing configuration
    2. Check for USB configuration
    3. Start captive portal if needed
    4. Run setup wizard
    5. Enroll with dashboard
    6. Save configuration
    """

    def __init__(self, config: Optional[ProvisioningConfig] = None):
        self.config = config or ProvisioningConfig()
        self._state = ProvisioningState.CHECKING

        # Components
        self._network = NetworkManager()
        self._captive_portal: Optional[CaptivePortal] = None
        self._setup_wizard: Optional[SetupWizard] = None
        self._usb_reader = USBConfigReader()
        self._enrollment: Optional[DashboardEnrollment] = None

        # Encryption for secure credential storage
        self._key_storage = create_key_storage(
            storage_type="auto",
            storage_path=Path(self.config.config_path) / "keys",
        )

        # Callbacks
        self._on_state_change: Optional[Callable[[ProvisioningState], None]] = None
        self._on_setup_complete: Optional[Callable[[Dict], None]] = None

        # State
        self._device_config: Optional[DeviceConfig] = None
        self._setup_data: Dict[str, Any] = {}

    @property
    def state(self) -> ProvisioningState:
        return self._state

    @property
    def is_configured(self) -> bool:
        """Check if device is already configured."""
        config_file = Path(self.config.config_path) / "config.yaml"
        return config_file.exists()

    async def initialize(self) -> bool:
        """Initialize provisioning service."""
        try:
            await self._network.initialize()
            logger.info("Provisioning service initialized")
            return True
        except Exception as e:
            logger.error(f"Provisioning init error: {e}")
            return False

    async def run(self) -> bool:
        """
        Run the provisioning workflow.

        Returns:
            True if device is configured
        """
        try:
            # Step 1: Check if already configured
            if self.is_configured:
                logger.info("Device already configured")
                self._set_state(ProvisioningState.CONFIGURED)
                return True

            # Step 2: Check for USB configuration
            self._set_state(ProvisioningState.CHECKING)
            usb_config = await self._check_usb_config()

            if usb_config:
                self._set_state(ProvisioningState.USB_CONFIG)
                success = await self._apply_usb_config(usb_config)
                if success:
                    self._set_state(ProvisioningState.CONFIGURED)
                    return True

            # Step 3: Start setup mode
            self._set_state(ProvisioningState.SETUP_MODE)
            success = await self._run_setup_mode()

            if success:
                # Step 4: Enroll with dashboard if configured
                if self._setup_data.get('dashboard', {}).get('url'):
                    self._set_state(ProvisioningState.ENROLLING)
                    await self._enroll_device()

                self._set_state(ProvisioningState.CONFIGURED)
                return True

            self._set_state(ProvisioningState.ERROR)
            return False

        except Exception as e:
            logger.error(f"Provisioning error: {e}")
            self._set_state(ProvisioningState.ERROR)
            return False

    async def _check_usb_config(self) -> Optional[DeviceConfig]:
        """Check for USB configuration file."""
        logger.info("Checking for USB configuration...")

        config_path = await self._usb_reader.find_config_file()
        if config_path:
            logger.info(f"Found USB config: {config_path}")
            return await self._usb_reader.read_config(config_path)

        return None

    async def _apply_usb_config(self, usb_config: DeviceConfig) -> bool:
        """Apply configuration from USB."""
        logger.info("Applying USB configuration...")

        try:
            # Configure WiFi if specified
            if usb_config.wifi_ssid:
                wifi_config = WiFiConfig(
                    ssid=usb_config.wifi_ssid,
                    password=usb_config.wifi_password,
                    hidden=usb_config.wifi_hidden,
                )

                if usb_config.wifi_enterprise:
                    wifi_config.security = WiFiSecurity.WPA_EAP
                    # Add enterprise settings...

                success = await self._network.connect_wifi(wifi_config)
                if not success:
                    logger.error("Failed to connect to WiFi from USB config")
                    return False

            # Save configuration
            await self._save_config({
                'device': {
                    'name': usb_config.name,
                    'location': usb_config.location,
                    'timezone': usb_config.timezone,
                },
                'meeting': {
                    'platform': usb_config.platform,
                    'email': usb_config.platform_email,
                    'password': usb_config.platform_password,
                },
                'dashboard': {
                    'url': usb_config.dashboard_url,
                    'enrollment_token': usb_config.enrollment_token,
                },
            })

            self._device_config = usb_config
            return True

        except Exception as e:
            logger.error(f"USB config apply error: {e}")
            return False

    async def _run_setup_mode(self) -> bool:
        """Run the setup mode with captive portal and wizard."""
        logger.info("Starting setup mode...")

        try:
            # Start captive portal
            ap_config = APConfig(
                ssid_prefix=self.config.ap_ssid_prefix,
                setup_timeout=self.config.setup_timeout,
            )
            self._captive_portal = CaptivePortal(ap_config)

            if not await self._captive_portal.start():
                logger.error("Failed to start captive portal")
                return False

            # Start setup wizard
            wizard_config = WizardConfig(
                port=self.config.wizard_port,
                timeout=self.config.setup_timeout,
            )
            self._setup_wizard = SetupWizard(wizard_config)

            # Register callbacks
            self._setup_wizard.on_wifi_configured(self._handle_wifi_configured)
            self._setup_wizard.on_setup_complete(self._handle_setup_complete)

            if not await self._setup_wizard.start():
                logger.error("Failed to start setup wizard")
                await self._captive_portal.stop()
                return False

            # Scan and provide WiFi networks
            networks = await self._network.scan_wifi_networks()
            self._setup_wizard.set_wifi_networks([
                {
                    'ssid': n.ssid,
                    'signal_strength': n.signal_strength,
                    'security': n.security.value,
                }
                for n in networks
            ])

            # Wait for setup to complete
            setup_complete = asyncio.Event()

            async def on_complete(data):
                self._setup_data = data
                setup_complete.set()

            self._setup_wizard.on_setup_complete(on_complete)

            # Wait with timeout
            try:
                await asyncio.wait_for(
                    setup_complete.wait(),
                    timeout=self.config.setup_timeout
                )
            except asyncio.TimeoutError:
                logger.warning("Setup timed out")
                return False

            # Cleanup
            await self._setup_wizard.stop()
            await self._captive_portal.stop()

            # Save configuration
            await self._save_config(self._setup_data)

            return True

        except Exception as e:
            logger.error(f"Setup mode error: {e}")
            return False

        finally:
            if self._setup_wizard:
                await self._setup_wizard.stop()
            if self._captive_portal:
                await self._captive_portal.stop()

    async def _handle_wifi_configured(self, wifi_data: Dict) -> bool:
        """Handle WiFi configuration from wizard."""
        try:
            wifi_config = WiFiConfig(
                ssid=wifi_data['ssid'],
                password=wifi_data.get('password'),
                hidden=wifi_data.get('hidden', False),
            )

            # Stop captive portal to allow real WiFi connection
            if self._captive_portal:
                await self._captive_portal.stop()

            # Connect to WiFi
            success = await self._network.connect_wifi(wifi_config)

            if not success:
                # Restart captive portal
                if self._captive_portal:
                    await self._captive_portal.start()
                return False

            # Verify connection
            await asyncio.sleep(3)
            if not await self._network.is_connected():
                if self._captive_portal:
                    await self._captive_portal.start()
                return False

            return True

        except Exception as e:
            logger.error(f"WiFi configuration error: {e}")
            return False

    async def _handle_setup_complete(self, setup_data: Dict) -> None:
        """Handle setup completion from wizard."""
        self._setup_data = setup_data

        if self._on_setup_complete:
            self._on_setup_complete(setup_data)

    async def _enroll_device(self) -> bool:
        """Enroll device with management dashboard."""
        dashboard_url = self._setup_data.get('dashboard', {}).get('url')
        enrollment_token = self._setup_data.get('dashboard', {}).get('enrollment_token')

        if not dashboard_url:
            return True  # No dashboard, skip enrollment

        try:
            self._enrollment = DashboardEnrollment(
                dashboard_url=dashboard_url,
                enrollment_token=enrollment_token,
            )

            result = await self._enrollment.enroll()

            if result.status == EnrollmentStatus.APPROVED:
                logger.info("Device enrolled successfully")

                # Apply any configuration from dashboard
                if result.config:
                    self._setup_data.update(result.config)

                return True

            elif result.status == EnrollmentStatus.PENDING:
                logger.info("Enrollment pending approval")
                # Continue without waiting

            else:
                logger.warning(f"Enrollment failed: {result.message}")

            return True  # Don't fail provisioning on enrollment issues

        except Exception as e:
            logger.error(f"Enrollment error: {e}")
            return True  # Don't fail provisioning

    async def _save_config(self, config_data: Dict) -> None:
        """Save configuration to disk."""
        config_dir = Path(self.config.config_path)
        config_dir.mkdir(parents=True, exist_ok=True)

        config_file = config_dir / "config.yaml"

        # Don't save passwords in plain text
        safe_config = {
            'device': config_data.get('device', {}),
            'meeting': {
                'platform': config_data.get('meeting', {}).get('platform'),
                'email': config_data.get('meeting', {}).get('email'),
                # Password stored separately in credentials store
            },
            'dashboard': {
                'url': config_data.get('dashboard', {}).get('url'),
            },
            'wifi': {
                'ssid': config_data.get('wifi', {}).get('ssid'),
            },
        }

        with open(config_file, 'w') as f:
            yaml.dump(safe_config, f, default_flow_style=False)

        logger.info(f"Configuration saved to {config_file}")

        # Save credentials separately with encryption
        await self._save_credentials(config_dir, config_data)

    async def _save_credentials(self, config_dir: Path, config_data: Dict) -> None:
        """
        Save credentials with AES-256-GCM encryption.

        Credentials are stored encrypted using the system's secure key storage
        (keyring, TPM, or encrypted file depending on availability).
        """
        credentials = {}

        # Collect credentials from config data
        if config_data.get('meeting', {}).get('password'):
            credentials['meeting_password'] = config_data['meeting']['password']

        if config_data.get('meeting', {}).get('email'):
            credentials['meeting_email'] = config_data['meeting']['email']

        if config_data.get('wifi', {}).get('password'):
            credentials['wifi_password'] = config_data['wifi']['password']

        if config_data.get('dashboard', {}).get('enrollment_token'):
            credentials['enrollment_token'] = config_data['dashboard']['enrollment_token']

        if not credentials:
            return

        # Get or create encryption key
        key_id = "croom_credentials"
        encryption_key = self._key_storage.retrieve_key(key_id)

        if encryption_key is None:
            # Generate new key and store it
            encryption_key = EncryptionService.generate_key()
            self._key_storage.store_key(key_id, encryption_key)

        # Create encryption service
        cipher = EncryptionService(encryption_key)

        # Encrypt and save each credential
        cred_dir = config_dir / "credentials"
        cred_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        for cred_name, cred_value in credentials.items():
            encrypted = cipher.encrypt_to_base64(cred_value)
            cred_file = cred_dir / f"{cred_name}.enc"

            with open(cred_file, 'w') as f:
                f.write(encrypted)

            # Set restrictive permissions
            cred_file.chmod(0o600)

        logger.info(f"Saved {len(credentials)} encrypted credentials")

    async def load_credential(self, credential_name: str) -> Optional[str]:
        """
        Load and decrypt a stored credential.

        Args:
            credential_name: Name of the credential (e.g., 'meeting_password')

        Returns:
            Decrypted credential value or None if not found
        """
        config_dir = Path(self.config.config_path)
        cred_file = config_dir / "credentials" / f"{credential_name}.enc"

        if not cred_file.exists():
            return None

        try:
            # Get encryption key
            key_id = "croom_credentials"
            encryption_key = self._key_storage.retrieve_key(key_id)

            if encryption_key is None:
                logger.error("Encryption key not found")
                return None

            # Decrypt
            cipher = EncryptionService(encryption_key)

            with open(cred_file, 'r') as f:
                encrypted = f.read()

            decrypted = cipher.decrypt_from_base64(encrypted)
            return decrypted.decode('utf-8')

        except Exception as e:
            logger.error(f"Failed to load credential {credential_name}: {e}")
            return None

    def _set_state(self, state: ProvisioningState) -> None:
        """Update provisioning state and notify listeners."""
        self._state = state
        logger.info(f"Provisioning state: {state.value}")

        if self._on_state_change:
            self._on_state_change(state)

    def on_state_change(self, callback: Callable[[ProvisioningState], None]) -> None:
        """Register callback for state changes."""
        self._on_state_change = callback

    def on_setup_complete(self, callback: Callable[[Dict], None]) -> None:
        """Register callback for setup completion."""
        self._on_setup_complete = callback

    def get_setup_display_info(self) -> Optional[Dict[str, Any]]:
        """Get information to display during setup."""
        if self._captive_portal and self._captive_portal.is_running:
            return self._captive_portal.get_display_info()
        return None

    async def shutdown(self) -> None:
        """Shutdown provisioning service."""
        if self._setup_wizard:
            await self._setup_wizard.stop()
        if self._captive_portal:
            await self._captive_portal.stop()

        logger.info("Provisioning service shutdown")


def create_provisioning_service(config: Dict[str, Any]) -> ProvisioningService:
    """
    Create a provisioning service from configuration.

    Args:
        config: Provisioning configuration dict

    Returns:
        Configured ProvisioningService instance
    """
    prov_config = ProvisioningConfig(
        config_path=config.get('config_path', '/etc/croom'),
        setup_timeout=config.get('setup_timeout', 1800),
        ap_ssid_prefix=config.get('ap_ssid_prefix', 'Croom-Setup'),
        wizard_port=config.get('wizard_port', 8080),
        auto_enroll=config.get('auto_enroll', True),
    )
    return ProvisioningService(prov_config)
