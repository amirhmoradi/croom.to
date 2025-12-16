"""
Display module for Croom.

Provides display management and HDMI-CEC control:
- HDMI-CEC commands (power, input switching)
- Display detection and info
- Screen management
"""

from croom.display.service import DisplayService, create_display_service
from croom.display.cec import (
    CECController,
    CECDevice,
    CECPowerStatus,
)

__all__ = [
    "DisplayService",
    "create_display_service",
    "CECController",
    "CECDevice",
    "CECPowerStatus",
]
