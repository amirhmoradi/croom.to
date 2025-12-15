"""
Webex provider.

Handles joining and controlling Cisco Webex meetings using browser automation.
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


class WebexProvider(MeetingProvider):
    """
    Cisco Webex meeting provider.

    Uses Playwright to join Webex meetings via the web client.
    Supports:
    - Webex Meetings
    - Webex Personal Room meetings
    - Webex Scheduled meetings
    """

    # URL patterns for Webex
    WEBEX_URL_PATTERNS = [
        # Standard Webex meeting link
        re.compile(r"([a-z0-9-]+)\.webex\.com/(?:meet|join)/([a-zA-Z0-9._-]+)", re.IGNORECASE),
        # Webex meeting with number
        re.compile(r"([a-z0-9-]+)\.webex\.com/([a-z0-9-]+)/j\.php\?MTID=([a-zA-Z0-9]+)", re.IGNORECASE),
        # Personal room
        re.compile(r"([a-z0-9-]+)\.webex\.com/meet/([a-zA-Z0-9._-]+)", re.IGNORECASE),
        # Webex events/webinars
        re.compile(r"([a-z0-9-]+)\.webex\.com/([a-z0-9-]+)/onstage/", re.IGNORECASE),
    ]

    def __init__(self):
        super().__init__()
        self._playwright = None
        self._browser: Optional["Browser"] = None
        self._context: Optional["BrowserContext"] = None
        self._page: Optional["Page"] = None
        self._site_name: str = ""

    @property
    def name(self) -> str:
        return "webex"

    @property
    def display_name(self) -> str:
        return "Cisco Webex"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        """Check if URL is a Webex meeting link."""
        url_lower = url.lower()
        if "webex.com" not in url_lower:
            return False

        for pattern in cls.WEBEX_URL_PATTERNS:
            if pattern.search(url):
                return True

        # Generic webex.com check
        return "webex.com" in url_lower and ("/meet/" in url_lower or "/join/" in url_lower or "j.php" in url_lower)

    @classmethod
    def extract_meeting_id(cls, url: str) -> Optional[str]:
        """Extract meeting ID from Webex URL."""
        for pattern in cls.WEBEX_URL_PATTERNS:
            match = pattern.search(url)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    # Return the meeting identifier (last group)
                    return groups[-1]

        # Try to extract from path
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2:
            return path_parts[-1]

        return None

    @classmethod
    def extract_site_name(cls, url: str) -> Optional[str]:
        """Extract Webex site name from URL."""
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # Extract subdomain (site name)
        if hostname.endswith(".webex.com"):
            site = hostname.replace(".webex.com", "")
            return site

        return None

    async def initialize(self) -> None:
        """Initialize browser for Webex."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed")

        logger.info("Initializing Webex provider...")

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
                # Webex-specific optimizations
                "--disable-features=WebRtcHideLocalIpsWithMdns",
                "--enable-features=WebRTC-H264WithOpenH264FFmpeg",
            ]
        )

        self._context = await self._browser.new_context(
            permissions=["camera", "microphone"],
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        self._page = await self._context.new_page()

        logger.info("Webex provider initialized")

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

        logger.info("Webex provider shutdown")

    async def join_meeting(
        self,
        meeting_url: str,
        display_name: str = "Conference Room",
        camera_on: bool = True,
        mic_on: bool = True
    ) -> MeetingInfo:
        """Join a Webex meeting via web client."""
        if not self._page:
            raise RuntimeError("Provider not initialized")

        meeting_id = self.extract_meeting_id(meeting_url)
        self._site_name = self.extract_site_name(meeting_url) or ""

        if not meeting_id:
            raise ValueError(f"Invalid Webex URL: {meeting_url}")

        # Parse password if present
        parsed = urlparse(meeting_url)
        query = parse_qs(parsed.query)
        password = query.get("password", query.get("pwd", [None]))[0]

        self._current_meeting = MeetingInfo(
            platform=self.name,
            meeting_id=meeting_id,
            meeting_url=meeting_url,
            is_camera_on=camera_on,
            is_muted=not mic_on
        )

        self._set_state(MeetingState.JOINING)
        logger.info(f"Joining Webex meeting: {meeting_id} on site {self._site_name}")

        try:
            # Navigate to meeting URL
            await self._page.goto(meeting_url, wait_until="networkidle")
            await asyncio.sleep(2)

            # Handle "Join from browser" option
            await self._select_browser_option()

            # Accept cookies/terms
            await self._accept_terms()

            # Handle guest login
            await self._handle_guest_login(display_name)

            # Handle password if required
            if password:
                await self._enter_password(password)

            # Configure media settings
            await self._configure_media(camera_on, mic_on)

            # Click join button
            await self._click_join_button()

            # Wait for connection
            await self._wait_for_connection()

            self._set_state(MeetingState.CONNECTED)
            logger.info(f"Connected to Webex meeting: {meeting_id}")

            return self._current_meeting

        except Exception as e:
            logger.error(f"Failed to join Webex meeting: {e}")
            self._current_meeting.error_message = str(e)
            self._set_state(MeetingState.ERROR)
            raise

    async def _select_browser_option(self) -> None:
        """Select browser join option instead of app."""
        try:
            # Look for "Join from your browser" or similar links
            selectors = [
                'a:has-text("Join from your browser")',
                'a:has-text("join from browser")',
                'button:has-text("Join from your browser")',
                '[data-test="guest-join-link"]',
                '.join-browser-link',
                'a[href*="launchApp=false"]',
            ]

            for selector in selectors:
                try:
                    link = await self._page.wait_for_selector(selector, timeout=5000)
                    if link:
                        await link.click()
                        await asyncio.sleep(2)
                        logger.debug("Selected browser join option")
                        return
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"No browser selection needed: {e}")

    async def _accept_terms(self) -> None:
        """Accept Webex terms, cookies, and privacy notices."""
        try:
            # Accept cookies
            cookie_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                'button:has-text("I Accept")',
                '[data-test="accept-cookies"]',
                '#onetrust-accept-btn-handler',
            ]

            for selector in cookie_selectors:
                try:
                    btn = await self._page.query_selector(selector)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(1)
                        break
                except Exception:
                    continue

        except Exception:
            pass

    async def _handle_guest_login(self, display_name: str) -> None:
        """Handle Webex guest join flow."""
        try:
            # Look for guest name input
            name_selectors = [
                'input[placeholder*="name" i]',
                'input[name="displayName"]',
                'input[data-test="guest-name"]',
                '#guest-name-input',
                'input[aria-label*="name" i]',
            ]

            for selector in name_selectors:
                try:
                    name_input = await self._page.wait_for_selector(selector, timeout=5000)
                    if name_input:
                        await name_input.fill("")
                        await name_input.fill(display_name)
                        logger.debug(f"Entered guest name: {display_name}")

                        # Also enter email if required
                        email_input = await self._page.query_selector(
                            'input[type="email"], input[placeholder*="email" i]'
                        )
                        if email_input:
                            await email_input.fill(f"{display_name.lower().replace(' ', '.')}@guest.local")

                        return
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"No guest login needed: {e}")

    async def _enter_password(self, password: str) -> None:
        """Enter meeting password if required."""
        try:
            pwd_selectors = [
                'input[type="password"]',
                'input[placeholder*="password" i]',
                'input[name="password"]',
                '[data-test="meeting-password"]',
            ]

            for selector in pwd_selectors:
                try:
                    pwd_input = await self._page.wait_for_selector(selector, timeout=3000)
                    if pwd_input:
                        await pwd_input.fill(password)
                        logger.debug("Entered meeting password")
                        return
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"No password entry needed: {e}")

    async def _configure_media(self, camera_on: bool, mic_on: bool) -> None:
        """Configure camera and microphone before joining."""
        try:
            # Handle camera toggle in pre-join
            if not camera_on:
                camera_selectors = [
                    'button[aria-label*="camera" i]',
                    'button[aria-label*="video" i]',
                    '[data-test="video-button"]',
                    '.video-preview-button',
                ]
                for selector in camera_selectors:
                    try:
                        btn = await self._page.query_selector(selector)
                        if btn:
                            # Check if camera is on (need to turn it off)
                            aria_label = await btn.get_attribute("aria-label") or ""
                            if "stop" in aria_label.lower() or "turn off" in aria_label.lower():
                                await btn.click()
                                await asyncio.sleep(0.5)
                            break
                    except Exception:
                        continue

            # Handle mic toggle in pre-join
            if not mic_on:
                mic_selectors = [
                    'button[aria-label*="mute" i]',
                    'button[aria-label*="microphone" i]',
                    '[data-test="audio-button"]',
                    '.audio-preview-button',
                ]
                for selector in mic_selectors:
                    try:
                        btn = await self._page.query_selector(selector)
                        if btn:
                            aria_label = await btn.get_attribute("aria-label") or ""
                            if "unmute" not in aria_label.lower():
                                await btn.click()
                                await asyncio.sleep(0.5)
                            break
                    except Exception:
                        continue

        except Exception as e:
            logger.debug(f"Could not configure media settings: {e}")

    async def _click_join_button(self) -> None:
        """Click Webex join button."""
        join_selectors = [
            'button:has-text("Join meeting")',
            'button:has-text("Join")',
            '[data-test="join-button"]',
            '[data-test="guest-join-button"]',
            'button.join-button',
            '[aria-label*="join" i]',
        ]

        for selector in join_selectors:
            try:
                btn = await self._page.wait_for_selector(selector, timeout=5000)
                if btn:
                    await btn.click()
                    logger.debug("Clicked join button")
                    return
            except Exception:
                continue

        raise RuntimeError("Could not find Webex join button")

    async def _wait_for_connection(self) -> None:
        """Wait for Webex meeting connection."""
        try:
            # Wait for meeting controls to appear (leave button)
            connection_indicators = [
                'button[aria-label*="leave" i]',
                '[data-test="leave-button"]',
                '.leave-meeting-button',
                'button:has-text("Leave")',
                # Or meeting toolbar
                '.meeting-controls-bar',
                '[data-test="meeting-controls"]',
            ]

            for indicator in connection_indicators:
                try:
                    await self._page.wait_for_selector(indicator, timeout=60000)
                    return
                except Exception:
                    continue

            # Check for lobby/waiting room
            lobby_indicators = [
                ':has-text("waiting for host")',
                ':has-text("lobby")',
                ':has-text("will let you in")',
            ]

            for indicator in lobby_indicators:
                lobby = await self._page.query_selector(indicator)
                if lobby:
                    self._set_state(MeetingState.IN_LOBBY)
                    logger.info("Waiting in Webex lobby...")

                    # Wait longer for host to admit
                    for conn_indicator in connection_indicators:
                        try:
                            await self._page.wait_for_selector(conn_indicator, timeout=300000)
                            return
                        except Exception:
                            continue

            raise RuntimeError("Failed to connect to Webex meeting")

        except Exception as e:
            # Check for specific error messages
            error_selectors = [
                ':has-text("meeting has ended")',
                ':has-text("meeting not started")',
                ':has-text("invalid meeting")',
            ]

            for selector in error_selectors:
                error = await self._page.query_selector(selector)
                if error:
                    text = await error.inner_text()
                    raise RuntimeError(f"Webex error: {text}")

            raise

    async def leave_meeting(self) -> None:
        """Leave Webex meeting."""
        if not self._page or self._state == MeetingState.IDLE:
            return

        self._set_state(MeetingState.LEAVING)
        logger.info("Leaving Webex meeting...")

        try:
            # Click leave button
            leave_selectors = [
                'button[aria-label*="leave" i]',
                '[data-test="leave-button"]',
                'button:has-text("Leave")',
                '.leave-meeting-button',
            ]

            for selector in leave_selectors:
                try:
                    leave_btn = await self._page.query_selector(selector)
                    if leave_btn:
                        await leave_btn.click()
                        await asyncio.sleep(0.5)
                        break
                except Exception:
                    continue

            # Confirm leave if dialog appears
            confirm_selectors = [
                'button:has-text("Leave meeting")',
                'button:has-text("Leave")',
                '[data-test="confirm-leave"]',
            ]

            for selector in confirm_selectors:
                try:
                    confirm = await self._page.query_selector(selector)
                    if confirm:
                        await confirm.click()
                        await asyncio.sleep(1)
                        break
                except Exception:
                    continue

            await self._page.goto("about:blank")

        except Exception as e:
            logger.error(f"Error leaving Webex: {e}")

        self._current_meeting = None
        self._set_state(MeetingState.IDLE)
        logger.info("Left Webex meeting")

    async def toggle_camera(self) -> bool:
        """Toggle Webex camera."""
        if not self._page or self._state != MeetingState.CONNECTED:
            return False

        try:
            video_selectors = [
                'button[aria-label*="video" i]',
                'button[aria-label*="camera" i]',
                '[data-test="video-button"]',
                '.video-button',
            ]

            for selector in video_selectors:
                try:
                    video_btn = await self._page.query_selector(selector)
                    if video_btn:
                        await video_btn.click()
                        await asyncio.sleep(0.5)

                        if self._current_meeting:
                            self._current_meeting.is_camera_on = not self._current_meeting.is_camera_on

                        return self._current_meeting.is_camera_on if self._current_meeting else False
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Failed to toggle Webex camera: {e}")
            return False

    async def toggle_mute(self) -> bool:
        """Toggle Webex mute."""
        if not self._page or self._state != MeetingState.CONNECTED:
            return True

        try:
            mute_selectors = [
                'button[aria-label*="mute" i]',
                'button[aria-label*="microphone" i]',
                '[data-test="audio-button"]',
                '.audio-button',
            ]

            for selector in mute_selectors:
                try:
                    mute_btn = await self._page.query_selector(selector)
                    if mute_btn:
                        await mute_btn.click()
                        await asyncio.sleep(0.5)

                        if self._current_meeting:
                            self._current_meeting.is_muted = not self._current_meeting.is_muted

                        return self._current_meeting.is_muted if self._current_meeting else True
                except Exception:
                    continue

            return True

        except Exception as e:
            logger.error(f"Failed to toggle Webex mute: {e}")
            return True

    async def share_screen(self) -> bool:
        """Start screen sharing in Webex."""
        if not self._page or self._state != MeetingState.CONNECTED:
            return False

        try:
            share_selectors = [
                'button[aria-label*="share" i]',
                '[data-test="share-button"]',
                'button:has-text("Share")',
            ]

            for selector in share_selectors:
                try:
                    share_btn = await self._page.query_selector(selector)
                    if share_btn:
                        await share_btn.click()
                        await asyncio.sleep(1)

                        # Select screen option
                        screen_option = await self._page.query_selector(
                            '[data-test="share-screen"], :has-text("Your Screen"), :has-text("Entire Screen")'
                        )
                        if screen_option:
                            await screen_option.click()
                            return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Failed to share screen in Webex: {e}")
            return False

    async def stop_share(self) -> bool:
        """Stop screen sharing in Webex."""
        if not self._page or self._state != MeetingState.CONNECTED:
            return False

        try:
            stop_selectors = [
                'button[aria-label*="stop sharing" i]',
                '[data-test="stop-share-button"]',
                'button:has-text("Stop")',
            ]

            for selector in stop_selectors:
                try:
                    stop_btn = await self._page.query_selector(selector)
                    if stop_btn:
                        await stop_btn.click()
                        await asyncio.sleep(0.5)
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Failed to stop sharing in Webex: {e}")
            return False

    async def raise_hand(self) -> bool:
        """Raise hand in Webex meeting."""
        if not self._page or self._state != MeetingState.CONNECTED:
            return False

        try:
            hand_selectors = [
                'button[aria-label*="raise hand" i]',
                '[data-test="raise-hand-button"]',
                'button:has-text("Raise")',
            ]

            for selector in hand_selectors:
                try:
                    hand_btn = await self._page.query_selector(selector)
                    if hand_btn:
                        await hand_btn.click()
                        await asyncio.sleep(0.5)
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Failed to raise hand in Webex: {e}")
            return False

    async def lower_hand(self) -> bool:
        """Lower hand in Webex meeting."""
        if not self._page or self._state != MeetingState.CONNECTED:
            return False

        try:
            lower_selectors = [
                'button[aria-label*="lower hand" i]',
                '[data-test="lower-hand-button"]',
                'button:has-text("Lower")',
            ]

            for selector in lower_selectors:
                try:
                    lower_btn = await self._page.query_selector(selector)
                    if lower_btn:
                        await lower_btn.click()
                        await asyncio.sleep(0.5)
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Failed to lower hand in Webex: {e}")
            return False

    async def send_reaction(self, reaction: str) -> bool:
        """Send a reaction in Webex (thumbs up, clap, etc.)."""
        if not self._page or self._state != MeetingState.CONNECTED:
            return False

        reaction_map = {
            "thumbs_up": "thumbs up",
            "clap": "clap",
            "heart": "heart",
            "laugh": "laugh",
            "surprised": "surprised",
            "sad": "sad",
        }

        reaction_text = reaction_map.get(reaction, reaction)

        try:
            # Open reactions menu
            reactions_btn = await self._page.query_selector(
                'button[aria-label*="reaction" i], [data-test="reactions-button"]'
            )
            if reactions_btn:
                await reactions_btn.click()
                await asyncio.sleep(0.5)

                # Select specific reaction
                reaction_option = await self._page.query_selector(
                    f'[aria-label*="{reaction_text}" i], :has-text("{reaction_text}")'
                )
                if reaction_option:
                    await reaction_option.click()
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to send reaction in Webex: {e}")
            return False
