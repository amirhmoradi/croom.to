"""
Calendar providers.

Each provider implements the CalendarProvider interface for
a specific calendar service.
"""

from croom.calendar.providers.base import CalendarProvider, CalendarEvent
from croom.calendar.providers.google import GoogleCalendarProvider
from croom.calendar.providers.microsoft import MicrosoftCalendarProvider


def get_provider(provider_name: str) -> type:
    """
    Get provider class by name.

    Args:
        provider_name: Provider name ('google', 'microsoft')

    Returns:
        Provider class
    """
    providers = {
        "google": GoogleCalendarProvider,
        "microsoft": MicrosoftCalendarProvider,
    }
    return providers.get(provider_name)


def get_all_providers() -> dict:
    """Get all available provider classes."""
    return {
        "google": GoogleCalendarProvider,
        "microsoft": MicrosoftCalendarProvider,
    }


__all__ = [
    "CalendarProvider",
    "CalendarEvent",
    "GoogleCalendarProvider",
    "MicrosoftCalendarProvider",
    "get_provider",
    "get_all_providers",
]
