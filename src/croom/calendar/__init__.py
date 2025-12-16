"""
Calendar integration for Croom.

Provides calendar synchronization and meeting scheduling:
- Google Calendar
- Microsoft 365 (Outlook)
"""

from croom.calendar.service import CalendarService, create_calendar_service
from croom.calendar.providers.base import (
    CalendarProvider,
    CalendarEvent,
    MeetingPlatform,
)
from croom.calendar.providers.google import GoogleCalendarProvider
from croom.calendar.providers.microsoft import MicrosoftCalendarProvider

__all__ = [
    "CalendarService",
    "create_calendar_service",
    "CalendarProvider",
    "CalendarEvent",
    "MeetingPlatform",
    "GoogleCalendarProvider",
    "MicrosoftCalendarProvider",
]
