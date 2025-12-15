"""
Croom - Enterprise Video Conferencing for Raspberry Pi

A cost-effective, enterprise-grade video conferencing solution
that rivals Cisco Webex Room Kit at a fraction of the cost.

Supports:
- Raspberry Pi 5 (primary)
- Raspberry Pi 4B (secondary)
- Ubuntu/Debian PCs (future, with abstraction layer)
"""

__version__ = "2.0.0-dev"
__author__ = "Croom Team"

from croom.core.agent import CroomAgent
from croom.core.config import Config
from croom.platform.detector import PlatformDetector

__all__ = [
    "CroomAgent",
    "Config",
    "PlatformDetector",
    "__version__",
]
