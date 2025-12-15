"""
Meeting platform providers.

Each provider implements the MeetingProvider interface for
a specific video conferencing platform.
"""

from croom.meeting.providers.base import MeetingProvider, MeetingInfo, MeetingState
from croom.meeting.providers.google_meet import GoogleMeetProvider
from croom.meeting.providers.teams import TeamsProvider
from croom.meeting.providers.zoom import ZoomProvider
from croom.meeting.providers.webex import WebexProvider


def get_provider(platform: str) -> type:
    """
    Get provider class for platform name.

    Args:
        platform: Platform name ('google_meet', 'teams', 'zoom', 'webex')

    Returns:
        Provider class
    """
    providers = {
        "google_meet": GoogleMeetProvider,
        "teams": TeamsProvider,
        "zoom": ZoomProvider,
        "webex": WebexProvider,
    }
    return providers.get(platform)


def get_all_providers() -> dict:
    """Get all available provider classes."""
    return {
        "google_meet": GoogleMeetProvider,
        "teams": TeamsProvider,
        "zoom": ZoomProvider,
        "webex": WebexProvider,
    }


__all__ = [
    "MeetingProvider",
    "MeetingInfo",
    "MeetingState",
    "GoogleMeetProvider",
    "TeamsProvider",
    "ZoomProvider",
    "WebexProvider",
    "get_provider",
    "get_all_providers",
]
