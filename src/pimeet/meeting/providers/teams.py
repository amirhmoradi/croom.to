"""
Microsoft Teams provider.

Handles joining and controlling Microsoft Teams meetings using browser automation.
"""

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse, parse_qs

from pimeet.meeting.providers.base import MeetingProvider, MeetingInfo, MeetingState

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class TeamsProvider(MeetingProvider):
    """
    Microsoft Teams meeting provider.

    Uses Playwright for browser automation to join Teams meetings
    via the web client.
    """

    # URL patterns for Teams
    TEAMS_URL_PATTERNS = [
        # Standard Teams meeting link
        re.compile(r"teams\.microsoft\.com/l/meetup-join/", re.IGNORECASE),
        # Teams live event
        re.compile(r"teams\.live\.com/meet/", re.IGNORECASE),
        # Short link
        re.compile(r"aka\.ms/", re.IGNORECASE),
    ]

    def __init__(self):
        super().__init__()
        self._playwright = None
        self._browser: Optional["Browser"] = None
        self._context: Optional["BrowserContext"] = None
        self._page: Optional["Page"] = None

    @property
    def name(self) -> str:
        return "teams"

    @property
    def display_name(self) -> str:
        return "Microsoft Teams"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        """Check if URL is a Teams meeting link."""
        for pattern in cls.TEAMS_URL_PATTERNS:
            if pattern.search(url):
                return True
        return "teams.microsoft.com" in url.lower() or "teams.live.com" in url.lower()

    @classmethod
    def extract_meeting_id(cls, url: str) -> Optional[str]:
        """Extract meeting ID from Teams URL."""
        # Teams URLs contain the meeting info in the path/query
        parsed = urlparse(url)

        # Try to extract from path
        if "/l/meetup-join/" in parsed.path:
            # Meeting ID is URL-encoded in the path
            parts = parsed.path.split("/")
            for i, part in enumerate(parts):
                if part == "meetup-join" and i + 1 < len(parts):
                    return parts[i + 1][:20]  # Truncate for readability

        # For other formats, use hash of URL
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:12]

    async def initialize(self) -> None:
        """Initialize browser for Teams."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed")

        logger.info("Initializing Teams provider...")

        self._playwright = await async_playwright().start()

        # Teams web works best with Edge/Chrome
        self._browser = await self._playwright.chromium.launch(
            headless=False,
            args=[
                "--use-fake-ui-for-media-stream",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--window-size=1920,1080",
            ]
        )

        self._context = await self._browser.new_context(
            permissions=["camera", "microphone"],
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        self._page = await self._context.new_page()

        logger.info("Teams provider initialized")

    async def shutdown(self) -> None:
        """Shutdown browser."""
        if self._state == MeetingState.CONNECTED:
            await self.leave_meeting()

        if self._page:
            await self._page.close()
            self._page = None

        if self._context:
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("Teams provider shutdown")

    async def join_meeting(
        self,
        meeting_url: str,
        display_name: str = "Conference Room",
        camera_on: bool = True,
        mic_on: bool = True
    ) -> MeetingInfo:
        """Join a Teams meeting."""
        if not self._page:
            raise RuntimeError("Provider not initialized")

        meeting_id = self.extract_meeting_id(meeting_url)

        self._current_meeting = MeetingInfo(
            platform=self.name,
            meeting_id=meeting_id,
            meeting_url=meeting_url,
            is_camera_on=camera_on,
            is_muted=not mic_on
        )

        self._set_state(MeetingState.JOINING)
        logger.info(f"Joining Teams meeting: {meeting_id}")

        try:
            # Navigate to meeting
            await self._page.goto(meeting_url, wait_until="networkidle")
            await asyncio.sleep(2)

            # Handle "Continue on this browser" option
            await self._select_browser_option()

            # Handle pre-join screen
            await self._handle_prejoin(display_name, camera_on, mic_on)

            # Click join button
            await self._click_join_button()

            # Wait for connection
            await self._wait_for_connection()

            self._set_state(MeetingState.CONNECTED)
            logger.info(f"Connected to Teams meeting: {meeting_id}")

            return self._current_meeting

        except Exception as e:
            logger.error(f"Failed to join Teams meeting: {e}")
            self._current_meeting.error_message = str(e)
            self._set_state(MeetingState.ERROR)
            raise

    async def _select_browser_option(self) -> None:
        """Select 'Continue on this browser' option."""
        try:
            # Look for browser option
            selectors = [
                'button:has-text("Continue on this browser")',
                'button:has-text("Join on the web")',
                '[data-tid="joinOnWeb"]',
            ]

            for selector in selectors:
                try:
                    btn = await self._page.wait_for_selector(selector, timeout=5000)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(2)
                        return
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"No browser selection needed: {e}")

    async def _handle_prejoin(
        self,
        display_name: str,
        camera_on: bool,
        mic_on: bool
    ) -> None:
        """Handle Teams pre-join screen."""
        # Set display name
        try:
            name_input = await self._page.wait_for_selector(
                'input[placeholder*="name" i], input[aria-label*="name" i]',
                timeout=5000
            )
            if name_input:
                await name_input.fill(display_name)
        except Exception:
            pass

        # Toggle camera
        if not camera_on:
            try:
                camera_btn = await self._page.query_selector(
                    '[aria-label*="camera" i][role="button"], button[aria-label*="video" i]'
                )
                if camera_btn:
                    aria_label = await camera_btn.get_attribute("aria-label")
                    if aria_label and ("on" in aria_label.lower() or "turn off" in aria_label.lower()):
                        await camera_btn.click()
            except Exception:
                pass

        # Toggle mic
        if not mic_on:
            try:
                mic_btn = await self._page.query_selector(
                    '[aria-label*="microphone" i][role="button"], button[aria-label*="mic" i]'
                )
                if mic_btn:
                    aria_label = await mic_btn.get_attribute("aria-label")
                    if aria_label and ("on" in aria_label.lower() or "unmute" in aria_label.lower()):
                        await mic_btn.click()
            except Exception:
                pass

    async def _click_join_button(self) -> None:
        """Click Teams join button."""
        join_selectors = [
            'button:has-text("Join now")',
            'button:has-text("Join meeting")',
            '[data-tid="prejoin-join-button"]',
            'button[aria-label*="Join" i]',
        ]

        for selector in join_selectors:
            try:
                btn = await self._page.wait_for_selector(selector, timeout=3000)
                if btn:
                    await btn.click()
                    return
            except Exception:
                continue

        raise RuntimeError("Could not find Teams join button")

    async def _wait_for_connection(self) -> None:
        """Wait for Teams meeting connection."""
        try:
            # Wait for hangup button (indicates connected)
            await self._page.wait_for_selector(
                '[aria-label*="hang up" i], [aria-label*="leave" i], [data-tid="hangup-main-btn"]',
                timeout=60000
            )
        except Exception:
            # Check for lobby
            lobby = await self._page.query_selector(':has-text("waiting")')
            if lobby:
                self._set_state(MeetingState.IN_LOBBY)
                logger.info("Waiting in Teams lobby...")
                await self._page.wait_for_selector(
                    '[aria-label*="hang up" i]',
                    timeout=300000
                )
            else:
                raise RuntimeError("Failed to connect to Teams meeting")

    async def leave_meeting(self) -> None:
        """Leave Teams meeting."""
        if not self._page or self._state == MeetingState.IDLE:
            return

        self._set_state(MeetingState.LEAVING)
        logger.info("Leaving Teams meeting...")

        try:
            # Click hangup button
            hangup_btn = await self._page.query_selector(
                '[aria-label*="hang up" i], [aria-label*="leave" i], [data-tid="hangup-main-btn"]'
            )
            if hangup_btn:
                await hangup_btn.click()
                await asyncio.sleep(1)

            await self._page.goto("about:blank")

        except Exception as e:
            logger.error(f"Error leaving Teams: {e}")

        self._current_meeting = None
        self._set_state(MeetingState.IDLE)
        logger.info("Left Teams meeting")

    async def toggle_camera(self) -> bool:
        """Toggle Teams camera."""
        if not self._page or self._state != MeetingState.CONNECTED:
            return False

        try:
            # Keyboard shortcut: Ctrl+Shift+O
            await self._page.keyboard.press("Control+Shift+o")
            await asyncio.sleep(0.5)

            if self._current_meeting:
                self._current_meeting.is_camera_on = not self._current_meeting.is_camera_on

            return self._current_meeting.is_camera_on if self._current_meeting else False

        except Exception as e:
            logger.error(f"Failed to toggle Teams camera: {e}")
            return False

    async def toggle_mute(self) -> bool:
        """Toggle Teams mute."""
        if not self._page or self._state != MeetingState.CONNECTED:
            return True

        try:
            # Keyboard shortcut: Ctrl+Shift+M
            await self._page.keyboard.press("Control+Shift+m")
            await asyncio.sleep(0.5)

            if self._current_meeting:
                self._current_meeting.is_muted = not self._current_meeting.is_muted

            return self._current_meeting.is_muted if self._current_meeting else True

        except Exception as e:
            logger.error(f"Failed to toggle Teams mute: {e}")
            return True
