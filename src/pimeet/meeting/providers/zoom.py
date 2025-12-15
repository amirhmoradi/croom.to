"""
Zoom provider.

Handles joining and controlling Zoom meetings using browser automation.
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


class ZoomProvider(MeetingProvider):
    """
    Zoom meeting provider.

    Uses Playwright to join Zoom meetings via the web client.
    Note: Zoom web client has limited functionality compared to native app.
    """

    # URL patterns for Zoom
    ZOOM_URL_PATTERNS = [
        # Standard Zoom meeting link
        re.compile(r"zoom\.us/j/(\d+)", re.IGNORECASE),
        # With password
        re.compile(r"zoom\.us/j/(\d+)\?pwd=", re.IGNORECASE),
        # Web client direct
        re.compile(r"zoom\.us/wc/(\d+)", re.IGNORECASE),
        # Zoomgov
        re.compile(r"zoomgov\.com/j/(\d+)", re.IGNORECASE),
    ]

    def __init__(self):
        super().__init__()
        self._playwright = None
        self._browser: Optional["Browser"] = None
        self._context: Optional["BrowserContext"] = None
        self._page: Optional["Page"] = None

    @property
    def name(self) -> str:
        return "zoom"

    @property
    def display_name(self) -> str:
        return "Zoom"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        """Check if URL is a Zoom meeting link."""
        for pattern in cls.ZOOM_URL_PATTERNS:
            if pattern.search(url):
                return True
        return "zoom.us" in url.lower() or "zoomgov.com" in url.lower()

    @classmethod
    def extract_meeting_id(cls, url: str) -> Optional[str]:
        """Extract meeting ID from Zoom URL."""
        for pattern in cls.ZOOM_URL_PATTERNS:
            match = pattern.search(url)
            if match:
                return match.group(1)
        return None

    async def initialize(self) -> None:
        """Initialize browser for Zoom."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed")

        logger.info("Initializing Zoom provider...")

        self._playwright = await async_playwright().start()

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

        logger.info("Zoom provider initialized")

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

        logger.info("Zoom provider shutdown")

    async def join_meeting(
        self,
        meeting_url: str,
        display_name: str = "Conference Room",
        camera_on: bool = True,
        mic_on: bool = True
    ) -> MeetingInfo:
        """Join a Zoom meeting via web client."""
        if not self._page:
            raise RuntimeError("Provider not initialized")

        meeting_id = self.extract_meeting_id(meeting_url)
        if not meeting_id:
            raise ValueError(f"Invalid Zoom URL: {meeting_url}")

        # Parse password if present
        parsed = urlparse(meeting_url)
        query = parse_qs(parsed.query)
        password = query.get("pwd", [None])[0]

        self._current_meeting = MeetingInfo(
            platform=self.name,
            meeting_id=meeting_id,
            meeting_url=meeting_url,
            is_camera_on=camera_on,
            is_muted=not mic_on
        )

        self._set_state(MeetingState.JOINING)
        logger.info(f"Joining Zoom meeting: {meeting_id}")

        try:
            # Construct web client URL
            web_url = f"https://zoom.us/wc/{meeting_id}/join"
            if password:
                web_url += f"?pwd={password}"

            # Navigate to web client
            await self._page.goto(web_url, wait_until="networkidle")
            await asyncio.sleep(2)

            # Handle "Join from Your Browser" link
            await self._select_browser_option()

            # Accept terms if needed
            await self._accept_terms()

            # Handle pre-join
            await self._handle_prejoin(display_name, camera_on, mic_on)

            # Click join
            await self._click_join_button()

            # Wait for connection
            await self._wait_for_connection()

            self._set_state(MeetingState.CONNECTED)
            logger.info(f"Connected to Zoom meeting: {meeting_id}")

            return self._current_meeting

        except Exception as e:
            logger.error(f"Failed to join Zoom meeting: {e}")
            self._current_meeting.error_message = str(e)
            self._set_state(MeetingState.ERROR)
            raise

    async def _select_browser_option(self) -> None:
        """Select browser join option."""
        try:
            # Look for "Join from Your Browser" link
            selectors = [
                'a:has-text("Join from Your Browser")',
                'a:has-text("join from your browser")',
                '#joinBtn',
            ]

            for selector in selectors:
                try:
                    link = await self._page.wait_for_selector(selector, timeout=5000)
                    if link:
                        await link.click()
                        await asyncio.sleep(2)
                        return
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"No browser selection needed: {e}")

    async def _accept_terms(self) -> None:
        """Accept Zoom terms and cookies."""
        try:
            # Accept cookies
            cookie_btn = await self._page.query_selector(
                'button:has-text("Accept"), button:has-text("I Agree")'
            )
            if cookie_btn:
                await cookie_btn.click()
                await asyncio.sleep(1)
        except Exception:
            pass

    async def _handle_prejoin(
        self,
        display_name: str,
        camera_on: bool,
        mic_on: bool
    ) -> None:
        """Handle Zoom pre-join screen."""
        # Set display name
        try:
            name_input = await self._page.wait_for_selector(
                '#inputname, input[placeholder*="name" i]',
                timeout=5000
            )
            if name_input:
                await name_input.fill(display_name)
        except Exception:
            pass

        # Enter password if prompted
        try:
            pwd_input = await self._page.query_selector(
                '#inputpasscode, input[type="password"]'
            )
            if pwd_input:
                # Password should be in URL, but prompt user if needed
                logger.warning("Zoom password required but not in URL")
        except Exception:
            pass

        # Note: Zoom web client controls camera/mic after joining
        # Store preferences to apply after connection

    async def _click_join_button(self) -> None:
        """Click Zoom join button."""
        join_selectors = [
            'button:has-text("Join")',
            '#joinBtn',
            'button.join-btn',
            '[aria-label*="join" i]',
        ]

        for selector in join_selectors:
            try:
                btn = await self._page.wait_for_selector(selector, timeout=3000)
                if btn:
                    await btn.click()
                    return
            except Exception:
                continue

        raise RuntimeError("Could not find Zoom join button")

    async def _wait_for_connection(self) -> None:
        """Wait for Zoom meeting connection."""
        try:
            # Wait for meeting controls to appear
            await self._page.wait_for_selector(
                '[aria-label*="leave" i], .leave-btn, button:has-text("Leave")',
                timeout=60000
            )
        except Exception:
            # Check for waiting room
            waiting = await self._page.query_selector(':has-text("waiting room")')
            if waiting:
                self._set_state(MeetingState.IN_LOBBY)
                logger.info("Waiting in Zoom waiting room...")
                await self._page.wait_for_selector(
                    '[aria-label*="leave" i]',
                    timeout=300000
                )
            else:
                raise RuntimeError("Failed to connect to Zoom meeting")

    async def leave_meeting(self) -> None:
        """Leave Zoom meeting."""
        if not self._page or self._state == MeetingState.IDLE:
            return

        self._set_state(MeetingState.LEAVING)
        logger.info("Leaving Zoom meeting...")

        try:
            # Click leave button
            leave_btn = await self._page.query_selector(
                '[aria-label*="leave" i], .leave-btn, button:has-text("Leave")'
            )
            if leave_btn:
                await leave_btn.click()
                await asyncio.sleep(0.5)

            # Confirm leave
            confirm = await self._page.query_selector(
                'button:has-text("Leave Meeting"), button:has-text("Leave")'
            )
            if confirm:
                await confirm.click()
                await asyncio.sleep(1)

            await self._page.goto("about:blank")

        except Exception as e:
            logger.error(f"Error leaving Zoom: {e}")

        self._current_meeting = None
        self._set_state(MeetingState.IDLE)
        logger.info("Left Zoom meeting")

    async def toggle_camera(self) -> bool:
        """Toggle Zoom camera."""
        if not self._page or self._state != MeetingState.CONNECTED:
            return False

        try:
            # Click video button
            video_btn = await self._page.query_selector(
                '[aria-label*="video" i], .video-btn, button:has-text("Start Video")'
            )
            if video_btn:
                await video_btn.click()
                await asyncio.sleep(0.5)

            if self._current_meeting:
                self._current_meeting.is_camera_on = not self._current_meeting.is_camera_on

            return self._current_meeting.is_camera_on if self._current_meeting else False

        except Exception as e:
            logger.error(f"Failed to toggle Zoom camera: {e}")
            return False

    async def toggle_mute(self) -> bool:
        """Toggle Zoom mute."""
        if not self._page or self._state != MeetingState.CONNECTED:
            return True

        try:
            # Click mute button
            mute_btn = await self._page.query_selector(
                '[aria-label*="mute" i], .mute-btn, button:has-text("Mute")'
            )
            if mute_btn:
                await mute_btn.click()
                await asyncio.sleep(0.5)

            if self._current_meeting:
                self._current_meeting.is_muted = not self._current_meeting.is_muted

            return self._current_meeting.is_muted if self._current_meeting else True

        except Exception as e:
            logger.error(f"Failed to toggle Zoom mute: {e}")
            return True
