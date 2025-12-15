"""
Calendar integration for PiMeet.

Provides calendar synchronization and meeting scheduling:
- Google Calendar
- Microsoft 365 (Outlook)
"""

from pimeet.calendar.service import CalendarService, create_calendar_service
from pimeet.calendar.providers.base import (
    CalendarProvider,
    CalendarEvent,
    MeetingPlatform,
)
from pimeet.calendar.providers.google import GoogleCalendarProvider
from pimeet.calendar.providers.microsoft import MicrosoftCalendarProvider

__all__ = [
    "CalendarService",
    "create_calendar_service",
    "CalendarProvider",
    "CalendarEvent",
    "MeetingPlatform",
    "GoogleCalendarProvider",
    "MicrosoftCalendarProvider",
]
