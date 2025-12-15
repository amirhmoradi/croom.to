"""
Microsoft 365 Calendar provider.

Uses Microsoft Graph API to fetch events from Outlook/Microsoft 365.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

import aiohttp

from pimeet.calendar.providers.base import (
    CalendarProvider,
    CalendarEvent,
    MeetingPlatform,
    detect_meeting_platform,
    extract_meeting_url,
)

logger = logging.getLogger(__name__)

# Microsoft authentication library
try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False


class MicrosoftCalendarProvider(CalendarProvider):
    """
    Microsoft 365 Calendar provider.

    Uses Microsoft Graph API for calendar access.
    Supports delegated (user) and application (service) permissions.
    """

    # API endpoints
    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    AUTHORITY = "https://login.microsoftonline.com"

    # Required scopes
    SCOPES = [
        "Calendars.Read",
    ]

    def __init__(self):
        super().__init__()
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._msal_app = None
        self._tenant_id: Optional[str] = None
        self._user_email: Optional[str] = None

    @property
    def name(self) -> str:
        return "microsoft"

    @property
    def display_name(self) -> str:
        return "Microsoft 365"

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with Microsoft Graph API.

        Supports:
        1. Client credentials (app-only) - for service accounts
        2. Device code flow - for user authentication
        3. Username/password (ROPC) - legacy, not recommended

        Args:
            credentials: Dict with:
                - 'client_id': Azure AD app client ID
                - 'client_secret': Client secret (for app-only)
                - 'tenant_id': Azure AD tenant ID
                - 'user_email': User email (for delegated access)

        Returns:
            True if authentication successful
        """
        if not MSAL_AVAILABLE:
            logger.error("MSAL library not installed: pip install msal")
            return False

        try:
            client_id = credentials.get('client_id')
            client_secret = credentials.get('client_secret')
            tenant_id = credentials.get('tenant_id', 'common')
            user_email = credentials.get('user_email')

            if not client_id:
                logger.error("client_id required for Microsoft authentication")
                return False

            self._tenant_id = tenant_id
            self._user_email = user_email
            authority = f"{self.AUTHORITY}/{tenant_id}"

            # App-only (client credentials) flow
            if client_secret and not user_email:
                self._msal_app = msal.ConfidentialClientApplication(
                    client_id,
                    authority=authority,
                    client_credential=client_secret,
                )

                # Acquire token for app
                result = self._msal_app.acquire_token_for_client(
                    scopes=["https://graph.microsoft.com/.default"]
                )

            # Delegated (user) flow with device code
            elif user_email:
                self._msal_app = msal.PublicClientApplication(
                    client_id,
                    authority=authority,
                )

                # Try to get cached token first
                accounts = self._msal_app.get_accounts(username=user_email)
                if accounts:
                    result = self._msal_app.acquire_token_silent(
                        self.SCOPES,
                        account=accounts[0]
                    )
                else:
                    # Need interactive authentication
                    # For device, use device code flow
                    flow = self._msal_app.initiate_device_flow(scopes=self.SCOPES)
                    if "user_code" in flow:
                        logger.info(f"Device code: {flow['user_code']}")
                        logger.info(f"Go to: {flow['verification_uri']}")
                        result = self._msal_app.acquire_token_by_device_flow(flow)
                    else:
                        logger.error("Failed to initiate device flow")
                        return False

            else:
                logger.error("Need either client_secret (app) or user_email (delegated)")
                return False

            if "access_token" in result:
                self._access_token = result["access_token"]
                self._token_expiry = datetime.now(timezone.utc) + timedelta(
                    seconds=result.get("expires_in", 3600)
                )
                self._authenticated = True
                self._credentials = credentials
                logger.info("Microsoft 365 authentication successful")
                return True
            else:
                logger.error(f"Authentication failed: {result.get('error_description')}")
                return False

        except Exception as e:
            logger.error(f"Microsoft authentication failed: {e}")
            self._authenticated = False
            return False

    async def refresh_auth(self) -> bool:
        """Refresh authentication tokens."""
        if not self._msal_app or not self._credentials:
            return False

        try:
            # Check if token needs refresh
            if self._token_expiry and datetime.now(timezone.utc) < self._token_expiry - timedelta(minutes=5):
                return True  # Token still valid

            # Re-authenticate
            return await self.authenticate(self._credentials)

        except Exception as e:
            logger.error(f"Failed to refresh Microsoft tokens: {e}")
            return False

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make authenticated request to Graph API."""
        if not self._access_token:
            await self.refresh_auth()

        if not self._access_token:
            return None

        url = f"{self.GRAPH_API_ENDPOINT}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error = await resp.text()
                    logger.error(f"Graph API error {resp.status}: {error}")
                    return None

    async def get_calendars(self) -> List[Dict[str, str]]:
        """Get list of available calendars."""
        if not self._authenticated:
            return []

        try:
            # For delegated permissions
            endpoint = "/me/calendars"

            # For app permissions, need to specify user
            if self._user_email and self._credentials.get('client_secret'):
                endpoint = f"/users/{self._user_email}/calendars"

            result = await self._make_request(endpoint)
            if not result:
                return []

            calendars = result.get('value', [])
            return [
                {
                    'id': cal['id'],
                    'name': cal.get('name', 'Calendar'),
                    'primary': cal.get('isDefaultCalendar', False),
                }
                for cal in calendars
            ]

        except Exception as e:
            logger.error(f"Failed to list calendars: {e}")
            return []

    async def get_events(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        max_results: int = 100
    ) -> List[CalendarEvent]:
        """Get events from Microsoft 365 Calendar."""
        if not self._authenticated:
            return []

        try:
            # Ensure timezone-aware
            if time_min.tzinfo is None:
                time_min = time_min.replace(tzinfo=timezone.utc)
            if time_max.tzinfo is None:
                time_max = time_max.replace(tzinfo=timezone.utc)

            # Build endpoint
            base = "/me"
            if self._user_email and self._credentials.get('client_secret'):
                base = f"/users/{self._user_email}"

            endpoint = f"{base}/calendars/{calendar_id}/events"

            params = {
                "$filter": f"start/dateTime ge '{time_min.isoformat()}' and start/dateTime le '{time_max.isoformat()}'",
                "$orderby": "start/dateTime",
                "$top": str(max_results),
                "$select": "id,subject,start,end,organizer,bodyPreview,location,onlineMeeting,onlineMeetingUrl,isAllDay,recurrence,isCancelled,attendees,responseStatus",
            }

            result = await self._make_request(endpoint, params=params)
            if not result:
                return []

            events = []
            for item in result.get('value', []):
                event = self._parse_event(item, calendar_id)
                if event:
                    events.append(event)

            logger.debug(f"Fetched {len(events)} events from {calendar_id}")
            return events

        except Exception as e:
            logger.error(f"Failed to fetch events: {e}")
            return []

    def _parse_event(self, item: Dict, calendar_id: str) -> Optional[CalendarEvent]:
        """Parse Microsoft Graph event to CalendarEvent."""
        try:
            # Parse times
            start = item.get('start', {})
            end = item.get('end', {})

            # Microsoft returns times in event's timezone
            start_dt = start.get('dateTime', '')
            end_dt = end.get('dateTime', '')

            if start_dt:
                # Add Z if no timezone info (assume UTC from API)
                if not start_dt.endswith('Z') and '+' not in start_dt:
                    start_dt += 'Z'
                start_time = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
            else:
                return None

            if end_dt:
                if not end_dt.endswith('Z') and '+' not in end_dt:
                    end_dt += 'Z'
                end_time = datetime.fromisoformat(end_dt.replace('Z', '+00:00'))
            else:
                return None

            # Get meeting URL
            meeting_url = None
            meeting_platform = MeetingPlatform.UNKNOWN

            # Check onlineMeeting first (Teams)
            online_meeting = item.get('onlineMeeting')
            if online_meeting:
                join_url = online_meeting.get('joinUrl')
                if join_url:
                    meeting_url = join_url
                    meeting_platform = MeetingPlatform.MICROSOFT_TEAMS

            # Also check onlineMeetingUrl
            if not meeting_url:
                meeting_url = item.get('onlineMeetingUrl')
                if meeting_url:
                    meeting_platform = detect_meeting_platform(meeting_url)

            # Check location and body for other meeting URLs
            if not meeting_url:
                location = item.get('location', {}).get('displayName', '')
                body = item.get('bodyPreview', '')

                url = extract_meeting_url(location) or extract_meeting_url(body)
                if url:
                    meeting_url = url
                    meeting_platform = detect_meeting_platform(url)

            # Get organizer
            organizer = item.get('organizer', {}).get('emailAddress', {}).get('address', '')

            # Get attendees
            attendees = [
                a.get('emailAddress', {}).get('address', '')
                for a in item.get('attendees', [])
            ]

            # Get response status
            response_status = item.get('responseStatus', {}).get('response', 'accepted')

            # Check if cancelled
            status = 'cancelled' if item.get('isCancelled') else 'confirmed'

            event = CalendarEvent(
                id=item['id'],
                title=item.get('subject', 'No Title'),
                start_time=start_time,
                end_time=end_time,
                meeting_url=meeting_url,
                meeting_platform=meeting_platform,
                organizer=organizer,
                description=item.get('bodyPreview', ''),
                location=item.get('location', {}).get('displayName', ''),
                calendar_id=calendar_id,
                is_all_day=item.get('isAllDay', False),
                is_recurring=bool(item.get('recurrence')),
                status=status,
                attendees=attendees,
                response_status=response_status,
            )

            return event

        except Exception as e:
            logger.error(f"Failed to parse event: {e}")
            return None
