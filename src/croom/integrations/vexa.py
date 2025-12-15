"""
Vexa integration for Croom.

Provides real-time meeting transcription and intelligence features
using the Vexa self-hosted transcription platform.

Vexa is an open-source (Apache 2.0) meeting transcription solution
that can be deployed on-premise for complete data sovereignty.

https://github.com/Vexa-ai/vexa
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import hashlib

logger = logging.getLogger(__name__)


class TranscriptionLanguage(Enum):
    """Supported transcription languages."""
    AUTO = "auto"
    ENGLISH = "en"
    FRENCH = "fr"
    GERMAN = "de"
    SPANISH = "es"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    POLISH = "pl"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ARABIC = "ar"
    HINDI = "hi"


class TranscriptionStatus(Enum):
    """Transcription session status."""
    CONNECTING = "connecting"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class VexaConfig:
    """
    Vexa service configuration.

    Attributes:
        server_url: Vexa server WebSocket URL
        api_url: Vexa REST API URL
        api_key: API key for authentication
        language: Primary transcription language
        enable_translation: Enable real-time translation
        translation_target: Target language for translation
        enable_summarization: Enable meeting summarization
        enable_action_items: Extract action items
        sample_rate: Audio sample rate (Hz)
        channels: Number of audio channels
        model: Whisper model to use
    """
    server_url: str
    api_url: str = ""
    api_key: Optional[str] = None
    language: TranscriptionLanguage = TranscriptionLanguage.AUTO
    enable_translation: bool = False
    translation_target: TranscriptionLanguage = TranscriptionLanguage.ENGLISH
    enable_summarization: bool = True
    enable_action_items: bool = True
    sample_rate: int = 16000
    channels: int = 1
    model: str = "base"  # tiny, base, small, medium, large

    @classmethod
    def for_local_deployment(
        cls,
        host: str = "localhost",
        port: int = 8000,
        **kwargs,
    ) -> "VexaConfig":
        """Create configuration for local Vexa deployment."""
        return cls(
            server_url=f"ws://{host}:{port}/ws/transcribe",
            api_url=f"http://{host}:{port}/api",
            **kwargs,
        )


@dataclass
class TranscriptionSegment:
    """
    A transcription segment.

    Attributes:
        segment_id: Unique segment identifier
        text: Transcribed text
        start_time: Start time (seconds from session start)
        end_time: End time (seconds from session start)
        speaker_id: Speaker identifier
        speaker_name: Speaker name (if identified)
        confidence: Transcription confidence score
        language: Detected language
        is_final: Whether this is final or interim result
        translation: Translated text (if enabled)
    """
    segment_id: str
    text: str
    start_time: float
    end_time: float
    speaker_id: Optional[str] = None
    speaker_name: Optional[str] = None
    confidence: float = 1.0
    language: Optional[str] = None
    is_final: bool = True
    translation: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "segment_id": self.segment_id,
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "confidence": self.confidence,
            "language": self.language,
            "is_final": self.is_final,
            "translation": self.translation,
        }


@dataclass
class ActionItem:
    """
    An extracted action item.

    Attributes:
        item_id: Unique identifier
        description: Action item description
        assignee: Person assigned
        due_date: Due date (if mentioned)
        priority: Priority level
        context: Context from the transcript
    """
    item_id: str
    description: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "normal"
    context: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "description": self.description,
            "assignee": self.assignee,
            "due_date": self.due_date,
            "priority": self.priority,
            "context": self.context,
        }


@dataclass
class MeetingSummary:
    """
    Meeting summary and insights.

    Attributes:
        summary_id: Unique identifier
        title: Meeting title
        summary: Executive summary
        key_points: List of key discussion points
        decisions: List of decisions made
        action_items: List of action items
        participants: List of participants
        duration: Meeting duration
        word_count: Total word count
        topics: Discussed topics
        sentiment: Overall sentiment analysis
        generated_at: When summary was generated
    """
    summary_id: str
    title: Optional[str] = None
    summary: str = ""
    key_points: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)
    participants: List[str] = field(default_factory=list)
    duration: float = 0.0
    word_count: int = 0
    topics: List[str] = field(default_factory=list)
    sentiment: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "summary_id": self.summary_id,
            "title": self.title,
            "summary": self.summary,
            "key_points": self.key_points,
            "decisions": self.decisions,
            "action_items": [item.to_dict() for item in self.action_items],
            "participants": self.participants,
            "duration": self.duration,
            "word_count": self.word_count,
            "topics": self.topics,
            "sentiment": self.sentiment,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class TranscriptionSession:
    """
    A transcription session.

    Attributes:
        session_id: Unique session identifier
        meeting_id: Associated meeting ID
        status: Current status
        language: Transcription language
        started_at: Session start time
        ended_at: Session end time
        segments: Transcription segments
        summary: Meeting summary (when available)
        metadata: Session metadata
    """
    session_id: str
    meeting_id: Optional[str] = None
    status: TranscriptionStatus = TranscriptionStatus.CONNECTING
    language: TranscriptionLanguage = TranscriptionLanguage.AUTO
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    segments: List[TranscriptionSegment] = field(default_factory=list)
    summary: Optional[MeetingSummary] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Get session duration in seconds."""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return (datetime.utcnow() - self.started_at).total_seconds()

    @property
    def full_transcript(self) -> str:
        """Get full transcript text."""
        return " ".join(seg.text for seg in self.segments if seg.is_final)

    @property
    def word_count(self) -> int:
        """Get word count."""
        return len(self.full_transcript.split())

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "meeting_id": self.meeting_id,
            "status": self.status.value,
            "language": self.language.value,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "segment_count": len(self.segments),
            "word_count": self.word_count,
            "duration": self.duration,
            "summary": self.summary.to_dict() if self.summary else None,
        }


class VexaClient:
    """
    Vexa transcription client.

    Provides real-time meeting transcription by streaming audio
    to a Vexa server and receiving transcription results.
    """

    def __init__(self, config: VexaConfig):
        """
        Initialize Vexa client.

        Args:
            config: Vexa configuration
        """
        self._config = config
        self._websocket = None
        self._session: Optional[TranscriptionSession] = None
        self._connected = False
        self._receive_task: Optional[asyncio.Task] = None

        # Callbacks
        self._on_segment: Optional[Callable[[TranscriptionSegment], None]] = None
        self._on_interim: Optional[Callable[[str], None]] = None
        self._on_summary: Optional[Callable[[MeetingSummary], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

        # Audio buffering
        self._audio_buffer = bytearray()
        self._buffer_threshold = 4096  # Send audio in chunks

    @property
    def is_connected(self) -> bool:
        """Check if connected to Vexa server."""
        return self._connected and self._websocket is not None

    @property
    def session(self) -> Optional[TranscriptionSession]:
        """Get current session."""
        return self._session

    async def connect(self, meeting_id: Optional[str] = None) -> bool:
        """
        Connect to Vexa server and start transcription session.

        Args:
            meeting_id: Optional meeting identifier

        Returns:
            True if connected successfully
        """
        try:
            import aiohttp

            # Generate session ID
            session_id = hashlib.sha256(
                f"{meeting_id or 'session'}:{time.time()}".encode()
            ).hexdigest()[:16]

            # Create session
            self._session = TranscriptionSession(
                session_id=session_id,
                meeting_id=meeting_id,
                status=TranscriptionStatus.CONNECTING,
                language=self._config.language,
            )

            # Build connection parameters
            params = {
                "session_id": session_id,
                "language": self._config.language.value,
                "sample_rate": self._config.sample_rate,
                "channels": self._config.channels,
                "model": self._config.model,
            }

            if self._config.enable_translation:
                params["translate"] = "true"
                params["target_language"] = self._config.translation_target.value

            url = f"{self._config.server_url}?{self._build_query_string(params)}"

            # Connect with headers
            headers = {}
            if self._config.api_key:
                headers["Authorization"] = f"Bearer {self._config.api_key}"

            # Create WebSocket connection
            self._ws_session = aiohttp.ClientSession()
            self._websocket = await self._ws_session.ws_connect(
                url,
                headers=headers,
                heartbeat=30,
            )

            self._connected = True
            self._session.status = TranscriptionStatus.ACTIVE

            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_loop())

            logger.info(f"Connected to Vexa server: session={session_id}")
            return True

        except Exception as e:
            logger.error(f"Vexa connection error: {e}")
            self._session.status = TranscriptionStatus.ERROR
            if self._on_error:
                self._on_error(str(e))
            return False

    async def disconnect(self) -> None:
        """Disconnect from Vexa server and finalize session."""
        if not self._connected:
            return

        try:
            # Send end of stream
            await self._send_message({"type": "end_stream"})

            # Wait for summary if enabled
            if self._config.enable_summarization:
                await asyncio.sleep(2)  # Allow time for summary generation

            # Close connection
            if self._websocket:
                await self._websocket.close()

            if self._receive_task:
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass

            if hasattr(self, '_ws_session'):
                await self._ws_session.close()

            self._connected = False

            if self._session:
                self._session.status = TranscriptionStatus.COMPLETED
                self._session.ended_at = datetime.utcnow()

            logger.info("Disconnected from Vexa server")

        except Exception as e:
            logger.error(f"Vexa disconnect error: {e}")

    async def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio data for transcription.

        Args:
            audio_data: Raw PCM audio data (16-bit signed, mono)
        """
        if not self._connected:
            return

        # Buffer audio
        self._audio_buffer.extend(audio_data)

        # Send when buffer reaches threshold
        while len(self._audio_buffer) >= self._buffer_threshold:
            chunk = bytes(self._audio_buffer[:self._buffer_threshold])
            del self._audio_buffer[:self._buffer_threshold]

            try:
                await self._websocket.send_bytes(chunk)
            except Exception as e:
                logger.error(f"Error sending audio: {e}")
                break

    async def _receive_loop(self) -> None:
        """Receive messages from Vexa server."""
        try:
            async for msg in self._websocket:
                if msg.type == 1:  # TEXT
                    await self._handle_message(json.loads(msg.data))
                elif msg.type == 2:  # BINARY
                    # Binary response (not typically used)
                    pass
                elif msg.type == 8:  # CLOSE
                    break
                elif msg.type == 256:  # ERROR
                    if self._on_error:
                        self._on_error(str(msg.data))
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
            if self._on_error:
                self._on_error(str(e))

    async def _handle_message(self, data: dict) -> None:
        """Handle a message from Vexa server."""
        msg_type = data.get("type", "")

        if msg_type == "transcript":
            # Final transcription segment
            segment = TranscriptionSegment(
                segment_id=data.get("id", ""),
                text=data.get("text", ""),
                start_time=data.get("start", 0),
                end_time=data.get("end", 0),
                speaker_id=data.get("speaker_id"),
                speaker_name=data.get("speaker"),
                confidence=data.get("confidence", 1.0),
                language=data.get("language"),
                is_final=True,
                translation=data.get("translation"),
            )

            if self._session:
                self._session.segments.append(segment)

            if self._on_segment:
                self._on_segment(segment)

        elif msg_type == "interim":
            # Interim/partial result
            if self._on_interim:
                self._on_interim(data.get("text", ""))

        elif msg_type == "summary":
            # Meeting summary
            summary = MeetingSummary(
                summary_id=data.get("id", ""),
                title=data.get("title"),
                summary=data.get("summary", ""),
                key_points=data.get("key_points", []),
                decisions=data.get("decisions", []),
                action_items=[
                    ActionItem(
                        item_id=item.get("id", ""),
                        description=item.get("description", ""),
                        assignee=item.get("assignee"),
                        due_date=item.get("due_date"),
                        priority=item.get("priority", "normal"),
                        context=item.get("context"),
                    )
                    for item in data.get("action_items", [])
                ],
                participants=data.get("participants", []),
                duration=data.get("duration", 0),
                word_count=data.get("word_count", 0),
                topics=data.get("topics", []),
                sentiment=data.get("sentiment"),
            )

            if self._session:
                self._session.summary = summary

            if self._on_summary:
                self._on_summary(summary)

        elif msg_type == "error":
            error_msg = data.get("message", "Unknown error")
            logger.error(f"Vexa error: {error_msg}")
            if self._on_error:
                self._on_error(error_msg)

        elif msg_type == "status":
            # Status update
            status = data.get("status")
            if status and self._session:
                try:
                    self._session.status = TranscriptionStatus(status)
                except ValueError:
                    pass

    async def _send_message(self, data: dict) -> None:
        """Send a JSON message to Vexa server."""
        if self._websocket:
            await self._websocket.send_str(json.dumps(data))

    def _build_query_string(self, params: dict) -> str:
        """Build URL query string."""
        return "&".join(f"{k}={v}" for k, v in params.items())

    def on_segment(self, callback: Callable[[TranscriptionSegment], None]) -> None:
        """Register callback for transcription segments."""
        self._on_segment = callback

    def on_interim(self, callback: Callable[[str], None]) -> None:
        """Register callback for interim results."""
        self._on_interim = callback

    def on_summary(self, callback: Callable[[MeetingSummary], None]) -> None:
        """Register callback for meeting summaries."""
        self._on_summary = callback

    def on_error(self, callback: Callable[[str], None]) -> None:
        """Register callback for errors."""
        self._on_error = callback

    async def request_summary(self) -> Optional[MeetingSummary]:
        """
        Request summary generation for current session.

        Returns:
            Meeting summary or None
        """
        if not self._connected or not self._session:
            return None

        try:
            await self._send_message({
                "type": "request_summary",
                "session_id": self._session.session_id,
            })

            # Wait for summary (with timeout)
            start = time.time()
            while time.time() - start < 30:
                if self._session.summary:
                    return self._session.summary
                await asyncio.sleep(0.5)

            return None

        except Exception as e:
            logger.error(f"Summary request error: {e}")
            return None

    async def get_session_transcript(
        self,
        session_id: str,
    ) -> Optional[List[TranscriptionSegment]]:
        """
        Get transcript for a completed session via REST API.

        Args:
            session_id: Session identifier

        Returns:
            List of transcription segments
        """
        if not self._config.api_url:
            return None

        try:
            import aiohttp

            headers = {}
            if self._config.api_key:
                headers["Authorization"] = f"Bearer {self._config.api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._config.api_url}/sessions/{session_id}/transcript",
                    headers=headers,
                ) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()

                    return [
                        TranscriptionSegment(
                            segment_id=seg.get("id", ""),
                            text=seg.get("text", ""),
                            start_time=seg.get("start", 0),
                            end_time=seg.get("end", 0),
                            speaker_id=seg.get("speaker_id"),
                            speaker_name=seg.get("speaker"),
                            confidence=seg.get("confidence", 1.0),
                            language=seg.get("language"),
                            is_final=True,
                        )
                        for seg in data.get("segments", [])
                    ]

        except Exception as e:
            logger.error(f"Transcript retrieval error: {e}")
            return None

    async def search_transcripts(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search across all transcripts.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching results
        """
        if not self._config.api_url:
            return []

        try:
            import aiohttp

            headers = {}
            if self._config.api_key:
                headers["Authorization"] = f"Bearer {self._config.api_key}"

            params = {"q": query, "limit": limit}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._config.api_url}/search",
                    headers=headers,
                    params=params,
                ) as response:
                    if response.status != 200:
                        return []

                    data = await response.json()
                    return data.get("results", [])

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []


class VexaService:
    """
    High-level Vexa service for Croom integration.

    Manages transcription sessions tied to Croom meetings.
    """

    def __init__(self, config: VexaConfig):
        """
        Initialize Vexa service.

        Args:
            config: Vexa configuration
        """
        self._config = config
        self._client: Optional[VexaClient] = None
        self._enabled = True

    @property
    def is_enabled(self) -> bool:
        """Check if Vexa integration is enabled."""
        return self._enabled

    @property
    def is_active(self) -> bool:
        """Check if transcription is active."""
        return self._client is not None and self._client.is_connected

    async def start_transcription(
        self,
        meeting_id: str,
        on_segment: Optional[Callable[[TranscriptionSegment], None]] = None,
        on_summary: Optional[Callable[[MeetingSummary], None]] = None,
    ) -> bool:
        """
        Start transcription for a meeting.

        Args:
            meeting_id: Meeting identifier
            on_segment: Callback for transcription segments
            on_summary: Callback for meeting summary

        Returns:
            True if started successfully
        """
        if not self._enabled:
            logger.info("Vexa transcription is disabled")
            return False

        if self._client and self._client.is_connected:
            logger.warning("Transcription already active")
            return False

        self._client = VexaClient(self._config)

        if on_segment:
            self._client.on_segment(on_segment)
        if on_summary:
            self._client.on_summary(on_summary)

        success = await self._client.connect(meeting_id)

        if success:
            logger.info(f"Started transcription for meeting: {meeting_id}")

        return success

    async def stop_transcription(self) -> Optional[MeetingSummary]:
        """
        Stop transcription and get summary.

        Returns:
            Meeting summary if available
        """
        if not self._client:
            return None

        # Request summary before disconnecting
        summary = None
        if self._config.enable_summarization:
            summary = await self._client.request_summary()

        await self._client.disconnect()

        # Get final summary from session
        if self._client.session and self._client.session.summary:
            summary = self._client.session.summary

        self._client = None

        return summary

    async def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio data for transcription.

        Args:
            audio_data: PCM audio data
        """
        if self._client:
            await self._client.send_audio(audio_data)

    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get current session information."""
        if self._client and self._client.session:
            return self._client.session.to_dict()
        return None

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable Vexa integration."""
        self._enabled = enabled

        if not enabled and self._client:
            asyncio.create_task(self.stop_transcription())


def create_vexa_service(config: Dict[str, Any]) -> VexaService:
    """
    Create Vexa service from configuration.

    Args:
        config: Vexa configuration dictionary

    Returns:
        Configured VexaService instance
    """
    vexa_config = VexaConfig(
        server_url=config.get("server_url", "ws://localhost:8000/ws/transcribe"),
        api_url=config.get("api_url", "http://localhost:8000/api"),
        api_key=config.get("api_key"),
        language=TranscriptionLanguage(config.get("language", "auto")),
        enable_translation=config.get("enable_translation", False),
        translation_target=TranscriptionLanguage(config.get("translation_target", "en")),
        enable_summarization=config.get("enable_summarization", True),
        enable_action_items=config.get("enable_action_items", True),
        sample_rate=config.get("sample_rate", 16000),
        channels=config.get("channels", 1),
        model=config.get("model", "base"),
    )

    return VexaService(vexa_config)
