"""
Device provisioning module for PiMeet.

Provides zero-touch device provisioning:
- Captive portal setup via WiFi AP
- USB configuration file support
- QR code setup
- Dashboard auto-registration
"""

from pimeet.provisioning.service import ProvisioningService, create_provisioning_service
from pimeet.provisioning.captive_portal import CaptivePortal
from pimeet.provisioning.usb_config import USBConfigReader
from pimeet.provisioning.network import NetworkManager
from pimeet.provisioning.enrollment import DashboardEnrollment

__all__ = [
    "ProvisioningService",
    "create_provisioning_service",
    "CaptivePortal",
    "USBConfigReader",
    "NetworkManager",
    "DashboardEnrollment",
]
