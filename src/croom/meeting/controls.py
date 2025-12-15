"""
Advanced meeting controls for Croom.

Provides unified interface for meeting controls across platforms including
screen sharing, hand raise, reactions, recording, and participant management.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ControlCapability(Enum):
    """Meeting control capabilities."""
    MUTE = "mute"
    CAMERA = "camera"
    SCREEN_SHARE = "screen_share"
    HAND_RAISE = "hand_raise"
    REACTIONS = "reactions"
    RECORDING = "recording"
    CHAT = "chat"
    LAYOUT = "layout"
    PARTICIPANTS = "participants"
    BREAKOUT_ROOMS = "breakout_rooms"
    WHITEBOARD = "whiteboard"
    CAPTIONS = "captions"
    VIRTUAL_BACKGROUND = "virtual_background"
    NOISE_SUPPRESSION = "noise_suppression"


class Reaction(Enum):
    """Meeting reactions."""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    CLAP = "clap"
    HEART = "heart"
    LAUGH = "laugh"
    SURPRISE = "surprise"
    RAISE_HAND = "raise_hand"
    LOWER_HAND = "lower_hand"


class LayoutMode(Enum):
    """Meeting layout modes."""
    GALLERY = "gallery"
    SPEAKER = "speaker"
    SPOTLIGHT = "spotlight"
    SIDEBAR = "sidebar"
    TILE = "tile"
    AUTO = "auto"


class RecordingState(Enum):
    """Recording state."""
    STOPPED = "stopped"
    STARTING = "starting"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPING = "stopping"


class ShareType(Enum):
    """Screen share types."""
    SCREEN = "screen"
    WINDOW = "window"
    TAB = "tab"
    AUDIO_ONLY = "audio_only"


@dataclass
class Participant:
    """Meeting participant information."""
    id: str
    name: str
    email: Optional[str] = None
    is_host: bool = False
    is_presenter: bool = False
    is_muted: bool = False
    is_camera_on: bool = False
    is_sharing: bool = False
    is_hand_raised: bool = False
    joined_at: Optional[datetime] = None
    avatar_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_host": self.is_host,
            "is_presenter": self.is_presenter,
            "is_muted": self.is_muted,
            "is_camera_on": self.is_camera_on,
            "is_sharing": self.is_sharing,
            "is_hand_raised": self.is_hand_raised,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "avatar_url": self.avatar_url,
        }


@dataclass
class ChatMessage:
    """Meeting chat message."""
    id: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    is_private: bool = False
    recipient_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "is_private": self.is_private,
            "recipient_id": self.recipient_id,
        }


@dataclass
class ScreenShareInfo:
    """Screen sharing information."""
    is_active: bool = False
    share_type: ShareType = ShareType.SCREEN
    source_name: Optional[str] = None
    is_audio_shared: bool = False
    started_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "is_active": self.is_active,
            "share_type": self.share_type.value,
            "source_name": self.source_name,
            "is_audio_shared": self.is_audio_shared,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }


@dataclass
class RecordingInfo:
    """Recording information."""
    state: RecordingState = RecordingState.STOPPED
    started_at: Optional[datetime] = None
    duration_seconds: int = 0
    is_cloud_recording: bool = True
    recording_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "duration_seconds": self.duration_seconds,
            "is_cloud_recording": self.is_cloud_recording,
            "recording_url": self.recording_url,
        }


class MeetingControlsInterface(ABC):
    """Abstract interface for meeting controls."""

    @abstractmethod
    def get_capabilities(self) -> List[ControlCapability]:
        """Get supported control capabilities."""
        pass

    # Screen sharing
    @abstractmethod
    async def start_screen_share(
        self,
        share_type: ShareType = ShareType.SCREEN,
        audio: bool = True,
    ) -> bool:
        """Start screen sharing."""
        pass

    @abstractmethod
    async def stop_screen_share(self) -> bool:
        """Stop screen sharing."""
        pass

    @abstractmethod
    def get_screen_share_info(self) -> ScreenShareInfo:
        """Get screen share status."""
        pass

    # Hand raise
    @abstractmethod
    async def raise_hand(self) -> bool:
        """Raise hand."""
        pass

    @abstractmethod
    async def lower_hand(self) -> bool:
        """Lower hand."""
        pass

    # Reactions
    @abstractmethod
    async def send_reaction(self, reaction: Reaction) -> bool:
        """Send a reaction."""
        pass

    # Recording
    @abstractmethod
    async def start_recording(self, cloud: bool = True) -> bool:
        """Start meeting recording."""
        pass

    @abstractmethod
    async def stop_recording(self) -> bool:
        """Stop meeting recording."""
        pass

    @abstractmethod
    async def pause_recording(self) -> bool:
        """Pause meeting recording."""
        pass

    @abstractmethod
    def get_recording_info(self) -> RecordingInfo:
        """Get recording status."""
        pass

    # Chat
    @abstractmethod
    async def send_chat_message(
        self,
        message: str,
        recipient_id: Optional[str] = None,
    ) -> bool:
        """Send a chat message."""
        pass

    @abstractmethod
    def get_chat_history(self, limit: int = 100) -> List[ChatMessage]:
        """Get chat message history."""
        pass

    # Layout
    @abstractmethod
    async def set_layout(self, layout: LayoutMode) -> bool:
        """Set meeting layout."""
        pass

    @abstractmethod
    def get_layout(self) -> LayoutMode:
        """Get current layout."""
        pass

    # Participants
    @abstractmethod
    def get_participants(self) -> List[Participant]:
        """Get participant list."""
        pass

    @abstractmethod
    async def mute_participant(self, participant_id: str) -> bool:
        """Mute a participant (host only)."""
        pass

    @abstractmethod
    async def remove_participant(self, participant_id: str) -> bool:
        """Remove a participant (host only)."""
        pass

    # Captions
    @abstractmethod
    async def enable_captions(self, language: str = "en") -> bool:
        """Enable live captions."""
        pass

    @abstractmethod
    async def disable_captions(self) -> bool:
        """Disable live captions."""
        pass


class BaseMeetingControls(MeetingControlsInterface):
    """Base implementation of meeting controls with common functionality."""

    def __init__(self):
        self._capabilities: List[ControlCapability] = [
            ControlCapability.MUTE,
            ControlCapability.CAMERA,
        ]
        self._screen_share = ScreenShareInfo()
        self._recording = RecordingInfo()
        self._layout = LayoutMode.AUTO
        self._participants: List[Participant] = []
        self._chat_history: List[ChatMessage] = []
        self._hand_raised = False
        self._captions_enabled = False

        # Event callbacks
        self._on_participant_joined: List[Callable[[Participant], None]] = []
        self._on_participant_left: List[Callable[[str], None]] = []
        self._on_chat_message: List[Callable[[ChatMessage], None]] = []
        self._on_screen_share_changed: List[Callable[[ScreenShareInfo], None]] = []
        self._on_recording_changed: List[Callable[[RecordingInfo], None]] = []

    def get_capabilities(self) -> List[ControlCapability]:
        return self._capabilities.copy()

    def has_capability(self, capability: ControlCapability) -> bool:
        """Check if a capability is supported."""
        return capability in self._capabilities

    # Event registration
    def on_participant_joined(self, callback: Callable[[Participant], None]) -> None:
        """Register callback for participant join events."""
        self._on_participant_joined.append(callback)

    def on_participant_left(self, callback: Callable[[str], None]) -> None:
        """Register callback for participant leave events."""
        self._on_participant_left.append(callback)

    def on_chat_message(self, callback: Callable[[ChatMessage], None]) -> None:
        """Register callback for chat messages."""
        self._on_chat_message.append(callback)

    def on_screen_share_changed(self, callback: Callable[[ScreenShareInfo], None]) -> None:
        """Register callback for screen share changes."""
        self._on_screen_share_changed.append(callback)

    def on_recording_changed(self, callback: Callable[[RecordingInfo], None]) -> None:
        """Register callback for recording state changes."""
        self._on_recording_changed.append(callback)

    # Emit events
    def _emit_participant_joined(self, participant: Participant) -> None:
        for callback in self._on_participant_joined:
            try:
                callback(participant)
            except Exception as e:
                logger.error(f"Participant joined callback error: {e}")

    def _emit_participant_left(self, participant_id: str) -> None:
        for callback in self._on_participant_left:
            try:
                callback(participant_id)
            except Exception as e:
                logger.error(f"Participant left callback error: {e}")

    def _emit_chat_message(self, message: ChatMessage) -> None:
        for callback in self._on_chat_message:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Chat message callback error: {e}")

    def _emit_screen_share_changed(self) -> None:
        for callback in self._on_screen_share_changed:
            try:
                callback(self._screen_share)
            except Exception as e:
                logger.error(f"Screen share callback error: {e}")

    def _emit_recording_changed(self) -> None:
        for callback in self._on_recording_changed:
            try:
                callback(self._recording)
            except Exception as e:
                logger.error(f"Recording callback error: {e}")

    # Default implementations (can be overridden by platform-specific classes)
    async def start_screen_share(
        self,
        share_type: ShareType = ShareType.SCREEN,
        audio: bool = True,
    ) -> bool:
        if not self.has_capability(ControlCapability.SCREEN_SHARE):
            logger.warning("Screen share not supported")
            return False
        return False

    async def stop_screen_share(self) -> bool:
        if not self.has_capability(ControlCapability.SCREEN_SHARE):
            return False
        self._screen_share.is_active = False
        self._emit_screen_share_changed()
        return True

    def get_screen_share_info(self) -> ScreenShareInfo:
        return self._screen_share

    async def raise_hand(self) -> bool:
        if not self.has_capability(ControlCapability.HAND_RAISE):
            return False
        self._hand_raised = True
        return True

    async def lower_hand(self) -> bool:
        if not self.has_capability(ControlCapability.HAND_RAISE):
            return False
        self._hand_raised = False
        return True

    async def send_reaction(self, reaction: Reaction) -> bool:
        if not self.has_capability(ControlCapability.REACTIONS):
            return False
        return False

    async def start_recording(self, cloud: bool = True) -> bool:
        if not self.has_capability(ControlCapability.RECORDING):
            return False
        self._recording.state = RecordingState.RECORDING
        self._recording.started_at = datetime.utcnow()
        self._recording.is_cloud_recording = cloud
        self._emit_recording_changed()
        return True

    async def stop_recording(self) -> bool:
        if not self.has_capability(ControlCapability.RECORDING):
            return False
        self._recording.state = RecordingState.STOPPED
        self._emit_recording_changed()
        return True

    async def pause_recording(self) -> bool:
        if not self.has_capability(ControlCapability.RECORDING):
            return False
        if self._recording.state == RecordingState.RECORDING:
            self._recording.state = RecordingState.PAUSED
            self._emit_recording_changed()
            return True
        return False

    def get_recording_info(self) -> RecordingInfo:
        return self._recording

    async def send_chat_message(
        self,
        message: str,
        recipient_id: Optional[str] = None,
    ) -> bool:
        if not self.has_capability(ControlCapability.CHAT):
            return False
        return False

    def get_chat_history(self, limit: int = 100) -> List[ChatMessage]:
        return self._chat_history[-limit:]

    async def set_layout(self, layout: LayoutMode) -> bool:
        if not self.has_capability(ControlCapability.LAYOUT):
            return False
        self._layout = layout
        return True

    def get_layout(self) -> LayoutMode:
        return self._layout

    def get_participants(self) -> List[Participant]:
        return self._participants.copy()

    def get_participant_count(self) -> int:
        """Get number of participants."""
        return len(self._participants)

    async def mute_participant(self, participant_id: str) -> bool:
        if not self.has_capability(ControlCapability.PARTICIPANTS):
            return False
        return False

    async def remove_participant(self, participant_id: str) -> bool:
        if not self.has_capability(ControlCapability.PARTICIPANTS):
            return False
        return False

    async def enable_captions(self, language: str = "en") -> bool:
        if not self.has_capability(ControlCapability.CAPTIONS):
            return False
        self._captions_enabled = True
        return True

    async def disable_captions(self) -> bool:
        if not self.has_capability(ControlCapability.CAPTIONS):
            return False
        self._captions_enabled = False
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get controls status."""
        return {
            "capabilities": [c.value for c in self._capabilities],
            "screen_share": self._screen_share.to_dict(),
            "recording": self._recording.to_dict(),
            "layout": self._layout.value,
            "participant_count": len(self._participants),
            "hand_raised": self._hand_raised,
            "captions_enabled": self._captions_enabled,
        }


class GoogleMeetControls(BaseMeetingControls):
    """Google Meet specific controls."""

    def __init__(self, browser_automation):
        super().__init__()
        self._browser = browser_automation
        self._capabilities = [
            ControlCapability.MUTE,
            ControlCapability.CAMERA,
            ControlCapability.SCREEN_SHARE,
            ControlCapability.HAND_RAISE,
            ControlCapability.REACTIONS,
            ControlCapability.CHAT,
            ControlCapability.LAYOUT,
            ControlCapability.CAPTIONS,
            ControlCapability.NOISE_SUPPRESSION,
        ]

    async def start_screen_share(
        self,
        share_type: ShareType = ShareType.SCREEN,
        audio: bool = True,
    ) -> bool:
        try:
            # Click present button
            await self._browser.click('[aria-label="Present now"]')
            await asyncio.sleep(0.5)

            # Select share type
            if share_type == ShareType.SCREEN:
                await self._browser.click('[data-value="entire-screen"]')
            elif share_type == ShareType.WINDOW:
                await self._browser.click('[data-value="window"]')
            elif share_type == ShareType.TAB:
                await self._browser.click('[data-value="chrome-tab"]')

            self._screen_share.is_active = True
            self._screen_share.share_type = share_type
            self._screen_share.is_audio_shared = audio
            self._screen_share.started_at = datetime.utcnow()
            self._emit_screen_share_changed()
            return True

        except Exception as e:
            logger.error(f"Failed to start screen share: {e}")
            return False

    async def stop_screen_share(self) -> bool:
        try:
            await self._browser.click('[aria-label="Stop presenting"]')
            return await super().stop_screen_share()
        except Exception as e:
            logger.error(f"Failed to stop screen share: {e}")
            return False

    async def raise_hand(self) -> bool:
        try:
            await self._browser.click('[aria-label="Raise hand"]')
            self._hand_raised = True
            return True
        except Exception as e:
            logger.error(f"Failed to raise hand: {e}")
            return False

    async def lower_hand(self) -> bool:
        try:
            await self._browser.click('[aria-label="Lower hand"]')
            self._hand_raised = False
            return True
        except Exception as e:
            logger.error(f"Failed to lower hand: {e}")
            return False

    async def send_reaction(self, reaction: Reaction) -> bool:
        try:
            # Open reactions menu
            await self._browser.click('[aria-label="Send a reaction"]')
            await asyncio.sleep(0.3)

            # Map reaction to button
            reaction_map = {
                Reaction.THUMBS_UP: "👍",
                Reaction.HEART: "❤️",
                Reaction.CLAP: "👏",
                Reaction.LAUGH: "😂",
                Reaction.SURPRISE: "😮",
            }

            emoji = reaction_map.get(reaction)
            if emoji:
                await self._browser.click(f'[aria-label="{emoji}"]')
                return True

            return False
        except Exception as e:
            logger.error(f"Failed to send reaction: {e}")
            return False

    async def send_chat_message(
        self,
        message: str,
        recipient_id: Optional[str] = None,
    ) -> bool:
        try:
            # Open chat panel
            await self._browser.click('[aria-label="Chat with everyone"]')
            await asyncio.sleep(0.3)

            # Type and send message
            await self._browser.type('textarea[aria-label="Send a message"]', message)
            await self._browser.press('Enter')
            return True
        except Exception as e:
            logger.error(f"Failed to send chat message: {e}")
            return False

    async def set_layout(self, layout: LayoutMode) -> bool:
        try:
            # Open more options
            await self._browser.click('[aria-label="More options"]')
            await asyncio.sleep(0.3)

            # Click change layout
            await self._browser.click('[aria-label="Change layout"]')
            await asyncio.sleep(0.3)

            # Select layout
            layout_map = {
                LayoutMode.GALLERY: "Tiled",
                LayoutMode.SPEAKER: "Spotlight",
                LayoutMode.SIDEBAR: "Sidebar",
                LayoutMode.AUTO: "Auto",
            }

            layout_name = layout_map.get(layout, "Auto")
            await self._browser.click(f'[aria-label="{layout_name}"]')

            self._layout = layout
            return True
        except Exception as e:
            logger.error(f"Failed to set layout: {e}")
            return False

    async def enable_captions(self, language: str = "en") -> bool:
        try:
            await self._browser.click('[aria-label="Turn on captions"]')
            self._captions_enabled = True
            return True
        except Exception as e:
            logger.error(f"Failed to enable captions: {e}")
            return False

    async def disable_captions(self) -> bool:
        try:
            await self._browser.click('[aria-label="Turn off captions"]')
            self._captions_enabled = False
            return True
        except Exception as e:
            logger.error(f"Failed to disable captions: {e}")
            return False


class TeamsControls(BaseMeetingControls):
    """Microsoft Teams specific controls."""

    def __init__(self, browser_automation):
        super().__init__()
        self._browser = browser_automation
        self._capabilities = [
            ControlCapability.MUTE,
            ControlCapability.CAMERA,
            ControlCapability.SCREEN_SHARE,
            ControlCapability.HAND_RAISE,
            ControlCapability.REACTIONS,
            ControlCapability.RECORDING,
            ControlCapability.CHAT,
            ControlCapability.LAYOUT,
            ControlCapability.BREAKOUT_ROOMS,
            ControlCapability.WHITEBOARD,
            ControlCapability.CAPTIONS,
            ControlCapability.VIRTUAL_BACKGROUND,
            ControlCapability.NOISE_SUPPRESSION,
        ]

    async def start_screen_share(
        self,
        share_type: ShareType = ShareType.SCREEN,
        audio: bool = True,
    ) -> bool:
        try:
            await self._browser.click('[aria-label="Share"]')
            await asyncio.sleep(0.5)

            if share_type == ShareType.SCREEN:
                await self._browser.click('[data-tid="share-screen"]')
            elif share_type == ShareType.WINDOW:
                await self._browser.click('[data-tid="share-window"]')

            if audio:
                # Enable system audio sharing
                await self._browser.click('[data-tid="include-system-audio"]')

            self._screen_share.is_active = True
            self._screen_share.share_type = share_type
            self._screen_share.is_audio_shared = audio
            self._screen_share.started_at = datetime.utcnow()
            self._emit_screen_share_changed()
            return True
        except Exception as e:
            logger.error(f"Failed to start screen share: {e}")
            return False

    async def start_recording(self, cloud: bool = True) -> bool:
        try:
            # Open more actions menu
            await self._browser.click('[aria-label="More actions"]')
            await asyncio.sleep(0.3)

            await self._browser.click('[aria-label="Start recording"]')

            self._recording.state = RecordingState.RECORDING
            self._recording.started_at = datetime.utcnow()
            self._recording.is_cloud_recording = True
            self._emit_recording_changed()
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False

    async def stop_recording(self) -> bool:
        try:
            await self._browser.click('[aria-label="More actions"]')
            await asyncio.sleep(0.3)
            await self._browser.click('[aria-label="Stop recording"]')

            self._recording.state = RecordingState.STOPPED
            self._emit_recording_changed()
            return True
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return False

    async def raise_hand(self) -> bool:
        try:
            await self._browser.click('[aria-label="Raise"]')
            self._hand_raised = True
            return True
        except Exception as e:
            logger.error(f"Failed to raise hand: {e}")
            return False

    async def send_reaction(self, reaction: Reaction) -> bool:
        try:
            await self._browser.click('[aria-label="Reactions"]')
            await asyncio.sleep(0.3)

            reaction_map = {
                Reaction.THUMBS_UP: "like",
                Reaction.HEART: "heart",
                Reaction.CLAP: "applause",
                Reaction.LAUGH: "laugh",
                Reaction.SURPRISE: "surprised",
            }

            reaction_id = reaction_map.get(reaction)
            if reaction_id:
                await self._browser.click(f'[data-tid="reaction-{reaction_id}"]')
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send reaction: {e}")
            return False


class ZoomControls(BaseMeetingControls):
    """Zoom specific controls."""

    def __init__(self, browser_automation):
        super().__init__()
        self._browser = browser_automation
        self._capabilities = [
            ControlCapability.MUTE,
            ControlCapability.CAMERA,
            ControlCapability.SCREEN_SHARE,
            ControlCapability.HAND_RAISE,
            ControlCapability.REACTIONS,
            ControlCapability.RECORDING,
            ControlCapability.CHAT,
            ControlCapability.LAYOUT,
            ControlCapability.BREAKOUT_ROOMS,
            ControlCapability.WHITEBOARD,
            ControlCapability.CAPTIONS,
            ControlCapability.VIRTUAL_BACKGROUND,
            ControlCapability.PARTICIPANTS,
        ]

    async def start_screen_share(
        self,
        share_type: ShareType = ShareType.SCREEN,
        audio: bool = True,
    ) -> bool:
        try:
            await self._browser.click('[aria-label="Share Screen"]')
            await asyncio.sleep(0.5)

            # Select share type in popup
            if share_type == ShareType.SCREEN:
                await self._browser.click('[data-tab="Desktop"]')
            elif share_type == ShareType.WINDOW:
                await self._browser.click('[data-tab="Application"]')

            if audio:
                await self._browser.click('[aria-label="Share sound"]')

            await self._browser.click('[aria-label="Share"]')

            self._screen_share.is_active = True
            self._screen_share.share_type = share_type
            self._screen_share.is_audio_shared = audio
            self._screen_share.started_at = datetime.utcnow()
            self._emit_screen_share_changed()
            return True
        except Exception as e:
            logger.error(f"Failed to start screen share: {e}")
            return False

    async def start_recording(self, cloud: bool = True) -> bool:
        try:
            await self._browser.click('[aria-label="Record"]')
            await asyncio.sleep(0.3)

            if cloud:
                await self._browser.click('[aria-label="Record to the Cloud"]')
            else:
                await self._browser.click('[aria-label="Record on this Computer"]')

            self._recording.state = RecordingState.RECORDING
            self._recording.started_at = datetime.utcnow()
            self._recording.is_cloud_recording = cloud
            self._emit_recording_changed()
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False

    async def raise_hand(self) -> bool:
        try:
            await self._browser.click('[aria-label="Reactions"]')
            await asyncio.sleep(0.3)
            await self._browser.click('[aria-label="Raise Hand"]')
            self._hand_raised = True
            return True
        except Exception as e:
            logger.error(f"Failed to raise hand: {e}")
            return False

    async def mute_participant(self, participant_id: str) -> bool:
        try:
            # Open participants panel
            await self._browser.click('[aria-label="Participants"]')
            await asyncio.sleep(0.3)

            # Find and mute participant
            await self._browser.click(f'[data-participant-id="{participant_id}"] [aria-label="Mute"]')
            return True
        except Exception as e:
            logger.error(f"Failed to mute participant: {e}")
            return False

    async def remove_participant(self, participant_id: str) -> bool:
        try:
            await self._browser.click('[aria-label="Participants"]')
            await asyncio.sleep(0.3)

            # More options for participant
            await self._browser.click(f'[data-participant-id="{participant_id}"] [aria-label="More"]')
            await asyncio.sleep(0.3)

            await self._browser.click('[aria-label="Remove"]')
            return True
        except Exception as e:
            logger.error(f"Failed to remove participant: {e}")
            return False


class WebexControls(BaseMeetingControls):
    """Cisco Webex specific controls."""

    def __init__(self, browser_automation):
        super().__init__()
        self._browser = browser_automation
        self._capabilities = [
            ControlCapability.MUTE,
            ControlCapability.CAMERA,
            ControlCapability.SCREEN_SHARE,
            ControlCapability.HAND_RAISE,
            ControlCapability.REACTIONS,
            ControlCapability.RECORDING,
            ControlCapability.CHAT,
            ControlCapability.LAYOUT,
            ControlCapability.BREAKOUT_ROOMS,
            ControlCapability.WHITEBOARD,
            ControlCapability.CAPTIONS,
            ControlCapability.VIRTUAL_BACKGROUND,
            ControlCapability.PARTICIPANTS,
            ControlCapability.NOISE_SUPPRESSION,
        ]

    async def start_screen_share(
        self,
        share_type: ShareType = ShareType.SCREEN,
        audio: bool = True,
    ) -> bool:
        try:
            # Click share button
            await self._browser.click('[data-test="share-button"], [aria-label*="share" i]')
            await asyncio.sleep(0.5)

            # Select share type
            if share_type == ShareType.SCREEN:
                await self._browser.click('[data-test="share-screen"], :has-text("Your Screen")')
            elif share_type == ShareType.WINDOW:
                await self._browser.click('[data-test="share-window"], :has-text("Window")')
            elif share_type == ShareType.TAB:
                await self._browser.click('[data-test="share-tab"], :has-text("Browser Tab")')

            # Enable audio sharing if requested
            if audio:
                audio_checkbox = await self._browser.query_selector(
                    '[data-test="share-audio"], [aria-label*="audio" i]'
                )
                if audio_checkbox:
                    await audio_checkbox.click()

            # Confirm share
            await self._browser.click('[data-test="share-confirm"], button:has-text("Share")')

            self._screen_share.is_active = True
            self._screen_share.share_type = share_type
            self._screen_share.is_audio_shared = audio
            self._screen_share.started_at = datetime.utcnow()
            self._emit_screen_share_changed()
            return True
        except Exception as e:
            logger.error(f"Failed to start Webex screen share: {e}")
            return False

    async def stop_screen_share(self) -> bool:
        try:
            await self._browser.click(
                '[data-test="stop-share"], [aria-label*="stop sharing" i], button:has-text("Stop")'
            )

            self._screen_share.is_active = False
            self._screen_share.stopped_at = datetime.utcnow()
            self._emit_screen_share_changed()
            return True
        except Exception as e:
            logger.error(f"Failed to stop Webex screen share: {e}")
            return False

    async def start_recording(self, cloud: bool = True) -> bool:
        try:
            # Open more menu
            await self._browser.click('[data-test="more-button"], [aria-label="More options"]')
            await asyncio.sleep(0.3)

            # Click record
            await self._browser.click('[data-test="record"], :has-text("Record")')
            await asyncio.sleep(0.3)

            # Select recording type
            if cloud:
                await self._browser.click('[data-test="record-cloud"], :has-text("Record to cloud")')
            else:
                await self._browser.click('[data-test="record-local"], :has-text("Record to computer")')

            self._recording.state = RecordingState.RECORDING
            self._recording.started_at = datetime.utcnow()
            self._recording.is_cloud_recording = cloud
            self._emit_recording_changed()
            return True
        except Exception as e:
            logger.error(f"Failed to start Webex recording: {e}")
            return False

    async def stop_recording(self) -> bool:
        try:
            await self._browser.click('[data-test="more-button"], [aria-label="More options"]')
            await asyncio.sleep(0.3)
            await self._browser.click('[data-test="stop-record"], :has-text("Stop recording")')

            self._recording.state = RecordingState.STOPPED
            self._emit_recording_changed()
            return True
        except Exception as e:
            logger.error(f"Failed to stop Webex recording: {e}")
            return False

    async def raise_hand(self) -> bool:
        try:
            await self._browser.click(
                '[data-test="raise-hand"], [aria-label*="raise hand" i], button:has-text("Raise")'
            )
            self._hand_raised = True
            return True
        except Exception as e:
            logger.error(f"Failed to raise hand in Webex: {e}")
            return False

    async def lower_hand(self) -> bool:
        try:
            await self._browser.click(
                '[data-test="lower-hand"], [aria-label*="lower hand" i], button:has-text("Lower")'
            )
            self._hand_raised = False
            return True
        except Exception as e:
            logger.error(f"Failed to lower hand in Webex: {e}")
            return False

    async def send_reaction(self, reaction: Reaction) -> bool:
        try:
            # Open reactions panel
            await self._browser.click('[data-test="reactions-button"], [aria-label*="reaction" i]')
            await asyncio.sleep(0.3)

            reaction_map = {
                Reaction.THUMBS_UP: "thumbs-up",
                Reaction.THUMBS_DOWN: "thumbs-down",
                Reaction.HEART: "heart",
                Reaction.CLAP: "clap",
                Reaction.LAUGH: "haha",
                Reaction.SURPRISE: "wow",
            }

            reaction_id = reaction_map.get(reaction)
            if reaction_id:
                await self._browser.click(f'[data-test="reaction-{reaction_id}"], [aria-label*="{reaction_id}" i]')
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send Webex reaction: {e}")
            return False

    async def set_layout(self, layout: LayoutMode) -> bool:
        try:
            # Open layout options
            await self._browser.click('[data-test="layout-button"], [aria-label*="layout" i]')
            await asyncio.sleep(0.3)

            layout_map = {
                LayoutMode.GALLERY: "grid",
                LayoutMode.SPEAKER: "stack",
                LayoutMode.SPOTLIGHT: "focus",
                LayoutMode.SIDEBAR: "side-by-side",
            }

            layout_id = layout_map.get(layout, "grid")
            await self._browser.click(f'[data-test="layout-{layout_id}"], [aria-label*="{layout_id}" i]')

            self._current_layout = layout
            return True
        except Exception as e:
            logger.error(f"Failed to set Webex layout: {e}")
            return False

    async def mute_participant(self, participant_id: str) -> bool:
        try:
            # Open participants panel
            await self._browser.click('[data-test="participants-button"], [aria-label*="participant" i]')
            await asyncio.sleep(0.3)

            # Find participant and mute
            await self._browser.click(
                f'[data-participant-id="{participant_id}"] [data-test="mute"], '
                f'[data-participant="{participant_id}"] [aria-label*="mute" i]'
            )
            return True
        except Exception as e:
            logger.error(f"Failed to mute Webex participant: {e}")
            return False

    async def remove_participant(self, participant_id: str) -> bool:
        try:
            await self._browser.click('[data-test="participants-button"], [aria-label*="participant" i]')
            await asyncio.sleep(0.3)

            # Open participant options
            await self._browser.click(
                f'[data-participant-id="{participant_id}"] [data-test="more"], '
                f'[data-participant="{participant_id}"] [aria-label="More"]'
            )
            await asyncio.sleep(0.3)

            # Remove from meeting
            await self._browser.click('[data-test="expel"], :has-text("Expel"), :has-text("Remove")')
            return True
        except Exception as e:
            logger.error(f"Failed to remove Webex participant: {e}")
            return False

    async def enable_captions(self) -> bool:
        try:
            await self._browser.click(
                '[data-test="captions-button"], [aria-label*="caption" i], button:has-text("Caption")'
            )
            return True
        except Exception as e:
            logger.error(f"Failed to enable Webex captions: {e}")
            return False

    async def send_chat_message(self, message: str, to: Optional[str] = None) -> bool:
        try:
            # Open chat panel
            await self._browser.click('[data-test="chat-button"], [aria-label*="chat" i]')
            await asyncio.sleep(0.3)

            # Type message
            await self._browser.fill('[data-test="chat-input"], [aria-label*="message" i]', message)

            # Send
            await self._browser.click('[data-test="send-chat"], [aria-label*="send" i]')

            chat_msg = ChatMessage(
                id=f"msg_{datetime.utcnow().timestamp()}",
                sender="self",
                content=message,
                timestamp=datetime.utcnow(),
                is_private=to is not None,
                recipient=to,
            )
            self._chat_messages.append(chat_msg)
            self._emit_chat_message(chat_msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send Webex chat message: {e}")
            return False


def get_controls_for_provider(provider_name: str, browser_automation) -> BaseMeetingControls:
    """
    Get controls instance for a meeting provider.

    Args:
        provider_name: Provider name (google_meet, teams, zoom, webex)
        browser_automation: Browser automation instance

    Returns:
        Controls instance for the provider
    """
    controls_map = {
        "google_meet": GoogleMeetControls,
        "teams": TeamsControls,
        "zoom": ZoomControls,
        "webex": WebexControls,
    }

    cls = controls_map.get(provider_name, BaseMeetingControls)
    return cls(browser_automation)
