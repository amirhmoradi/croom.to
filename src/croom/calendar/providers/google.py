"""
Google Calendar provider.

Uses Google Calendar API to fetch events and meeting information.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from croom.calendar.providers.base import (
    CalendarProvider,
    CalendarEvent,
    MeetingPlatform,
    detect_meeting_platform,
    extract_meeting_url,
)

logger = logging.getLogger(__name__)

# Google API dependencies
try:
    from google.oauth2.credentials import Credentials
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


class GoogleCalendarProvider(CalendarProvider):
    """
    Google Calendar provider.

    Supports OAuth2 user credentials and service account authentication.
    """

    # API scopes needed
    SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly',
    ]

    def __init__(self):
        super().__init__()
        self._service = None
        self._creds = None

    @property
    def name(self) -> str:
        return "google"

    @property
    def display_name(self) -> str:
        return "Google Calendar"

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with Google Calendar API.

        Supports two authentication methods:
        1. Service account (preferred for room devices)
        2. OAuth2 user credentials

        Args:
            credentials: Dict with either:
                - 'service_account_file': Path to service account JSON
                - 'service_account_info': Service account JSON dict
                - 'oauth_token': OAuth2 token info dict

        Returns:
            True if authentication successful
        """
        if not GOOGLE_API_AVAILABLE:
            logger.error("Google API libraries not installed")
            return False

        try:
            # Service account authentication (preferred)
            if 'service_account_file' in credentials:
                self._creds = ServiceAccountCredentials.from_service_account_file(
                    credentials['service_account_file'],
                    scopes=self.SCOPES
                )
                # Delegate to room account if specified
                if 'delegate_email' in credentials:
                    self._creds = self._creds.with_subject(credentials['delegate_email'])

            elif 'service_account_info' in credentials:
                self._creds = ServiceAccountCredentials.from_service_account_info(
                    credentials['service_account_info'],
                    scopes=self.SCOPES
                )
                if 'delegate_email' in credentials:
                    self._creds = self._creds.with_subject(credentials['delegate_email'])

            # OAuth2 token authentication
            elif 'oauth_token' in credentials:
                token_info = credentials['oauth_token']
                self._creds = Credentials(
                    token=token_info.get('access_token'),
                    refresh_token=token_info.get('refresh_token'),
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=token_info.get('client_id'),
                    client_secret=token_info.get('client_secret'),
                    scopes=self.SCOPES
                )
            else:
                logger.error("No valid credentials provided")
                return False

            # Build service
            self._service = build('calendar', 'v3', credentials=self._creds)

            # Test authentication
            self._service.calendarList().list(maxResults=1).execute()

            self._authenticated = True
            self._credentials = credentials
            logger.info("Google Calendar authentication successful")
            return True

        except Exception as e:
            logger.error(f"Google Calendar authentication failed: {e}")
            self._authenticated = False
            return False

    async def refresh_auth(self) -> bool:
        """Refresh authentication tokens."""
        if not self._creds:
            return False

        try:
            if self._creds.expired and self._creds.refresh_token:
                self._creds.refresh(Request())
                logger.info("Google Calendar tokens refreshed")
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to refresh Google tokens: {e}")
            return False

    async def get_calendars(self) -> List[Dict[str, str]]:
        """Get list of available calendars."""
        if not self._authenticated or not self._service:
            return []

        try:
            result = self._service.calendarList().list().execute()
            calendars = result.get('items', [])

            return [
                {
                    'id': cal['id'],
                    'name': cal.get('summary', cal['id']),
                    'primary': cal.get('primary', False),
                }
                for cal in calendars
            ]

        except HttpError as e:
            logger.error(f"Failed to list calendars: {e}")
            return []

    async def get_events(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        max_results: int = 100
    ) -> List[CalendarEvent]:
        """Get events from Google Calendar."""
        if not self._authenticated or not self._service:
            return []

        try:
            # Ensure timezone-aware
            if time_min.tzinfo is None:
                time_min = time_min.replace(tzinfo=timezone.utc)
            if time_max.tzinfo is None:
                time_max = time_max.replace(tzinfo=timezone.utc)

            result = self._service.events().list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = []
            for item in result.get('items', []):
                event = self._parse_event(item, calendar_id)
                if event:
                    events.append(event)

            logger.debug(f"Fetched {len(events)} events from {calendar_id}")
            return events

        except HttpError as e:
            logger.error(f"Failed to fetch events: {e}")
            return []

    def _parse_event(self, item: Dict, calendar_id: str) -> Optional[CalendarEvent]:
        """Parse Google Calendar API event to CalendarEvent."""
        try:
            # Get start/end times
            start = item.get('start', {})
            end = item.get('end', {})

            # Handle all-day events
            is_all_day = 'date' in start
            if is_all_day:
                start_time = datetime.fromisoformat(start['date'])
                end_time = datetime.fromisoformat(end['date'])
            else:
                start_time = datetime.fromisoformat(
                    start.get('dateTime', '').replace('Z', '+00:00')
                )
                end_time = datetime.fromisoformat(
                    end.get('dateTime', '').replace('Z', '+00:00')
                )

            # Get meeting URL
            meeting_url = None
            meeting_platform = MeetingPlatform.UNKNOWN

            # Check conferenceData first (Google Meet)
            conf_data = item.get('conferenceData', {})
            entry_points = conf_data.get('entryPoints', [])
            for ep in entry_points:
                if ep.get('entryPointType') == 'video':
                    meeting_url = ep.get('uri')
                    meeting_platform = MeetingPlatform.GOOGLE_MEET
                    break

            # If no conference data, check description/location
            if not meeting_url:
                description = item.get('description', '')
                location = item.get('location', '')

                url = extract_meeting_url(location) or extract_meeting_url(description)
                if url:
                    meeting_url = url
                    meeting_platform = detect_meeting_platform(url)

            # Get organizer
            organizer = item.get('organizer', {}).get('email', '')

            # Get attendees
            attendees = [
                a.get('email', '')
                for a in item.get('attendees', [])
            ]

            # Get response status for this calendar
            response_status = 'accepted'
            for a in item.get('attendees', []):
                if a.get('self'):
                    response_status = a.get('responseStatus', 'accepted')
                    break

            event = CalendarEvent(
                id=item['id'],
                title=item.get('summary', 'No Title'),
                start_time=start_time,
                end_time=end_time,
                meeting_url=meeting_url,
                meeting_platform=meeting_platform,
                organizer=organizer,
                description=item.get('description', ''),
                location=item.get('location', ''),
                calendar_id=calendar_id,
                is_all_day=is_all_day,
                is_recurring=bool(item.get('recurringEventId')),
                recurrence_id=item.get('recurringEventId'),
                status=item.get('status', 'confirmed'),
                attendees=attendees,
                response_status=response_status,
            )

            return event

        except Exception as e:
            logger.error(f"Failed to parse event: {e}")
            return None


# OAuth2 helper for initial setup
class GoogleOAuthHelper:
    """Helper class for OAuth2 authentication flow."""

    SCOPES = GoogleCalendarProvider.SCOPES

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    def get_auth_url(self, redirect_uri: str = 'urn:ietf:wg:oauth:2.0:oob') -> str:
        """Get OAuth2 authorization URL."""
        if not GOOGLE_API_AVAILABLE:
            raise RuntimeError("Google API libraries not installed")

        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                'installed': {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                }
            },
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        return auth_url

    def exchange_code(
        self,
        code: str,
        redirect_uri: str = 'urn:ietf:wg:oauth:2.0:oob'
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        if not GOOGLE_API_AVAILABLE:
            raise RuntimeError("Google API libraries not installed")

        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                'installed': {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                }
            },
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )

        flow.fetch_token(code=code)
        creds = flow.credentials

        return {
            'access_token': creds.token,
            'refresh_token': creds.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'expiry': creds.expiry.isoformat() if creds.expiry else None,
        }
