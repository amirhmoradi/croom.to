"""
PiMeet - Enterprise Video Conferencing for Raspberry Pi

A cost-effective, enterprise-grade video conferencing solution
that rivals Cisco Webex Room Kit at a fraction of the cost.

Supports:
- Raspberry Pi 5 (primary)
- Raspberry Pi 4B (secondary)
- Ubuntu/Debian PCs (future, with abstraction layer)
"""

__version__ = "2.0.0-dev"
__author__ = "PiMeet Team"

from pimeet.core.agent import PiMeetAgent
from pimeet.core.config import Config
from pimeet.platform.detector import PlatformDetector

__all__ = [
    "PiMeetAgent",
    "Config",
    "PlatformDetector",
    "__version__",
]
