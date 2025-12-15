"""
Meeting platform support for PiMeet.

Provides integration with video conferencing platforms:
- Google Meet
- Microsoft Teams
- Zoom
"""

from pimeet.meeting.service import MeetingService
from pimeet.meeting.providers.base import MeetingProvider, MeetingInfo, MeetingState

__all__ = [
    "MeetingService",
    "MeetingProvider",
    "MeetingInfo",
    "MeetingState",
]
