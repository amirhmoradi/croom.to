"""
Dashboard client module for PiMeet.

Provides communication between PiMeet devices and the management dashboard:
- WebSocket real-time connection
- Metrics reporting
- Remote command execution
- Configuration sync
"""

from pimeet.dashboard.client import DashboardClient, create_dashboard_client
from pimeet.dashboard.metrics import MetricsCollector, DeviceMetrics

__all__ = [
    "DashboardClient",
    "create_dashboard_client",
    "MetricsCollector",
    "DeviceMetrics",
]
