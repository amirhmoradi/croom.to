"""
Speaker tracking module for PiMeet.

Provides audio-visual speaker detection and tracking for intelligent
camera direction during meetings.
"""

import asyncio
import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class SpeakerState(Enum):
    """Speaker activity state."""
    SILENT = "silent"
    SPEAKING = "speaking"
    RECENTLY_SPOKE = "recently_spoke"


@dataclass
class AudioLevel:
    """Audio level measurement."""
    level_db: float
    rms: float
    peak: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SpeakerInfo:
    """Information about a detected speaker."""
    track_id: int
    position: Tuple[float, float]  # Normalized position
    audio_level: float
    state: SpeakerState
    confidence: float
    speaking_duration: float = 0
    last_spoke: Optional[datetime] = None
    word_count: int = 0

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "position": self.position,
            "audio_level": self.audio_level,
            "state": self.state.value,
            "confidence": self.confidence,
            "speaking_duration": self.speaking_duration,
            "last_spoke": self.last_spoke.isoformat() if self.last_spoke else None,
            "word_count": self.word_count,
        }


class AudioActivityDetector:
    """Detects speech activity from audio signals."""

    def __init__(
        self,
        sample_rate: int = 48000,
        frame_size: int = 480,  # 10ms at 48kHz
        speech_threshold_db: float = -40,
        silence_threshold_db: float = -50,
        min_speech_duration: float = 0.1,
        hangover_time: float = 0.3,
    ):
        self._sample_rate = sample_rate
        self._frame_size = frame_size
        self._speech_threshold = 10 ** (speech_threshold_db / 20)
        self._silence_threshold = 10 ** (silence_threshold_db / 20)
        self._min_speech_frames = int(min_speech_duration * sample_rate / frame_size)
        self._hangover_frames = int(hangover_time * sample_rate / frame_size)

        self._speech_frames = 0
        self._hangover_counter = 0
        self._is_speaking = False
        self._level_history: Deque[float] = deque(maxlen=100)

    def process_audio(self, audio: np.ndarray) -> Tuple[bool, float]:
        """
        Process audio frame and detect speech activity.

        Args:
            audio: Audio samples (float32, -1 to 1)

        Returns:
            Tuple of (is_speaking, audio_level_db)
        """
        # Calculate RMS level
        rms = np.sqrt(np.mean(audio ** 2))
        level_db = 20 * np.log10(max(rms, 1e-10))

        self._level_history.append(rms)

        # Adaptive threshold based on recent history
        if len(self._level_history) > 10:
            noise_floor = np.percentile(list(self._level_history), 10)
            adaptive_threshold = max(self._speech_threshold, noise_floor * 3)
        else:
            adaptive_threshold = self._speech_threshold

        # Speech detection with hangover
        if rms > adaptive_threshold:
            self._speech_frames += 1
            self._hangover_counter = self._hangover_frames

            if self._speech_frames >= self._min_speech_frames:
                self._is_speaking = True
        else:
            self._speech_frames = 0

            if self._hangover_counter > 0:
                self._hangover_counter -= 1
            else:
                self._is_speaking = False

        return self._is_speaking, level_db

    def reset(self) -> None:
        """Reset detector state."""
        self._speech_frames = 0
        self._hangover_counter = 0
        self._is_speaking = False
        self._level_history.clear()


class SpeakerLocalizer:
    """Localizes speaker position using audio beamforming or video."""

    def __init__(
        self,
        mic_positions: Optional[List[Tuple[float, float, float]]] = None,
        use_video_tracking: bool = True,
    ):
        """
        Initialize speaker localizer.

        Args:
            mic_positions: 3D positions of microphones for beamforming
            use_video_tracking: Use video face tracking for localization
        """
        self._mic_positions = mic_positions
        self._use_video = use_video_tracking
        self._sample_rate = 48000

    def localize_from_audio(
        self,
        audio_channels: List[np.ndarray],
    ) -> Optional[Tuple[float, float]]:
        """
        Estimate speaker direction from multi-channel audio.

        Uses GCC-PHAT (Generalized Cross-Correlation with Phase Transform)
        for time-delay estimation.

        Args:
            audio_channels: List of audio arrays, one per microphone

        Returns:
            Normalized (x, y) position estimate or None
        """
        if not self._mic_positions or len(audio_channels) < 2:
            return None

        # GCC-PHAT between first two channels
        try:
            signal1 = audio_channels[0]
            signal2 = audio_channels[1]

            # FFT
            n = len(signal1) + len(signal2) - 1
            fft1 = np.fft.rfft(signal1, n)
            fft2 = np.fft.rfft(signal2, n)

            # Cross-correlation with phase transform
            gcc = fft1 * np.conj(fft2)
            gcc_phat = gcc / (np.abs(gcc) + 1e-10)

            # Inverse FFT
            correlation = np.fft.irfft(gcc_phat)

            # Find peak
            max_shift = int(self._sample_rate * 0.002)  # Max 2ms delay
            center = len(correlation) // 2
            search_region = correlation[center - max_shift:center + max_shift]
            peak_idx = np.argmax(search_region) - max_shift

            # Convert to time delay
            time_delay = peak_idx / self._sample_rate

            # Convert to angle (simplified 2D)
            mic_dist = 0.1  # 10cm mic spacing
            speed_of_sound = 343  # m/s
            angle = np.arcsin(np.clip(time_delay * speed_of_sound / mic_dist, -1, 1))

            # Convert angle to normalized x position
            x = 0.5 + np.sin(angle) * 0.5
            y = 0.5  # Assume centered vertically

            return (x, y)

        except Exception as e:
            logger.debug(f"Audio localization error: {e}")
            return None

    def localize_from_video(
        self,
        face_positions: List[Tuple[float, float]],
        audio_levels: Dict[int, float],
    ) -> Optional[Tuple[int, Tuple[float, float]]]:
        """
        Match speaker to detected face using audio correlation.

        Args:
            face_positions: List of normalized face center positions
            audio_levels: Audio levels keyed by track ID

        Returns:
            Tuple of (track_id, position) for most likely speaker
        """
        if not face_positions or not audio_levels:
            return None

        # Find track with highest audio level
        max_level_track = max(audio_levels.items(), key=lambda x: x[1])
        track_id = max_level_track[0]

        # Get position for this track
        if track_id < len(face_positions):
            return (track_id, face_positions[track_id])

        return None


class SpeakerTracker:
    """Tracks speakers over time with audio-visual fusion."""

    def __init__(
        self,
        speaking_threshold_db: float = -35,
        recently_spoke_timeout: float = 2.0,
        history_size: int = 300,
    ):
        self._speaking_threshold = speaking_threshold_db
        self._recently_spoke_timeout = timedelta(seconds=recently_spoke_timeout)
        self._history_size = history_size

        # Per-person tracking
        self._speakers: Dict[int, SpeakerInfo] = {}
        self._audio_detectors: Dict[int, AudioActivityDetector] = {}

        # Global audio
        self._localizer = SpeakerLocalizer()
        self._active_speaker_id: Optional[int] = None

        # History
        self._speaker_history: Deque[Tuple[datetime, int]] = deque(maxlen=history_size)

        # Callbacks
        self._on_speaker_change: List[Callable[[Optional[int], SpeakerInfo], None]] = []

    def update(
        self,
        person_positions: Dict[int, Tuple[float, float]],
        audio_levels: Dict[int, float],
        lip_activity: Optional[Dict[int, float]] = None,
    ) -> Optional[int]:
        """
        Update speaker tracking with new observations.

        Args:
            person_positions: Track ID to normalized center position
            audio_levels: Track ID to audio level in dB
            lip_activity: Optional lip movement scores per track

        Returns:
            Track ID of current active speaker, or None
        """
        now = datetime.utcnow()

        # Update speaker states
        for track_id, position in person_positions.items():
            audio_level = audio_levels.get(track_id, -60)
            lip_score = lip_activity.get(track_id, 0) if lip_activity else 0

            # Get or create speaker info
            if track_id not in self._speakers:
                self._speakers[track_id] = SpeakerInfo(
                    track_id=track_id,
                    position=position,
                    audio_level=audio_level,
                    state=SpeakerState.SILENT,
                    confidence=0.5,
                )

            speaker = self._speakers[track_id]
            speaker.position = position
            speaker.audio_level = audio_level

            # Determine speaking state
            is_speaking = audio_level > self._speaking_threshold

            # Combine with lip activity if available
            if lip_activity:
                lip_speaking = lip_score > 0.5
                # Audio-visual fusion
                is_speaking = is_speaking and lip_speaking or (is_speaking and lip_score > 0.3)
                speaker.confidence = min(1.0, (audio_level + 60) / 30 * lip_score)
            else:
                speaker.confidence = min(1.0, (audio_level + 60) / 30)

            # Update state
            if is_speaking:
                if speaker.state != SpeakerState.SPEAKING:
                    speaker.state = SpeakerState.SPEAKING
                    speaker.speaking_duration = 0
                else:
                    speaker.speaking_duration += 0.033  # Assuming ~30fps
                speaker.last_spoke = now
            elif speaker.last_spoke and (now - speaker.last_spoke) < self._recently_spoke_timeout:
                speaker.state = SpeakerState.RECENTLY_SPOKE
            else:
                speaker.state = SpeakerState.SILENT
                speaker.speaking_duration = 0

        # Clean up old tracks
        active_ids = set(person_positions.keys())
        for track_id in list(self._speakers.keys()):
            if track_id not in active_ids:
                del self._speakers[track_id]

        # Find active speaker
        speaking = [
            s for s in self._speakers.values()
            if s.state == SpeakerState.SPEAKING
        ]

        new_speaker_id = None
        if speaking:
            # Prefer speaker with highest audio level * confidence
            best = max(speaking, key=lambda s: s.audio_level * s.confidence)
            new_speaker_id = best.track_id

        # Emit change if speaker changed
        if new_speaker_id != self._active_speaker_id:
            old_id = self._active_speaker_id
            self._active_speaker_id = new_speaker_id

            speaker_info = self._speakers.get(new_speaker_id) if new_speaker_id else None
            self._emit_speaker_change(new_speaker_id, speaker_info)

            if new_speaker_id:
                self._speaker_history.append((now, new_speaker_id))

        return self._active_speaker_id

    def get_active_speaker(self) -> Optional[SpeakerInfo]:
        """Get currently active speaker."""
        if self._active_speaker_id:
            return self._speakers.get(self._active_speaker_id)
        return None

    def get_all_speakers(self) -> List[SpeakerInfo]:
        """Get all tracked speakers."""
        return list(self._speakers.values())

    def get_speaker_stats(self) -> Dict[str, Any]:
        """Get speaker statistics."""
        total_speaking_time = sum(
            s.speaking_duration for s in self._speakers.values()
        )

        speaker_times = {
            s.track_id: s.speaking_duration
            for s in self._speakers.values()
        }

        return {
            "total_speakers": len(self._speakers),
            "active_speaker": self._active_speaker_id,
            "total_speaking_time": total_speaking_time,
            "speaker_times": speaker_times,
            "speaking_distribution": {
                sid: time / total_speaking_time if total_speaking_time > 0 else 0
                for sid, time in speaker_times.items()
            },
        }

    def reset(self) -> None:
        """Reset tracker state."""
        self._speakers.clear()
        self._audio_detectors.clear()
        self._active_speaker_id = None
        self._speaker_history.clear()

    # Callbacks
    def on_speaker_change(
        self,
        callback: Callable[[Optional[int], SpeakerInfo], None],
    ) -> None:
        self._on_speaker_change.append(callback)

    def _emit_speaker_change(
        self,
        speaker_id: Optional[int],
        speaker_info: Optional[SpeakerInfo],
    ) -> None:
        for callback in self._on_speaker_change:
            try:
                callback(speaker_id, speaker_info)
            except Exception as e:
                logger.error(f"Speaker change callback error: {e}")


class SpeakerTrackingService:
    """High-level service for speaker tracking integration."""

    def __init__(
        self,
        ai_service,
        audio_service,
        auto_framing_service=None,
    ):
        self._ai_service = ai_service
        self._audio_service = audio_service
        self._auto_framing = auto_framing_service
        self._tracker = SpeakerTracker()

        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Connect to auto-framing if available
        if self._auto_framing:
            self._tracker.on_speaker_change(self._on_speaker_change)

    async def start(self) -> None:
        """Start speaker tracking service."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("Speaker tracking service started")

    async def stop(self) -> None:
        """Stop speaker tracking service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._tracker.reset()
        logger.info("Speaker tracking service stopped")

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                # Get audio levels from audio service
                audio_levels = await self._audio_service.get_source_levels()

                # Get person positions from AI detections
                # This would normally come from the detection pipeline
                person_positions = {}

                # Update tracker
                self._tracker.update(person_positions, audio_levels)

            except Exception as e:
                logger.error(f"Speaker tracking error: {e}")

            await asyncio.sleep(0.033)

    def _on_speaker_change(
        self,
        speaker_id: Optional[int],
        speaker_info: Optional[SpeakerInfo],
    ) -> None:
        """Handle speaker change for auto-framing."""
        if self._auto_framing and speaker_id:
            from pimeet.ai.auto_framing import FramingMode
            engine = self._auto_framing.engine

            if engine.mode == FramingMode.SPEAKER:
                engine.select_person(speaker_id)

    @property
    def tracker(self) -> SpeakerTracker:
        return self._tracker

    def get_active_speaker(self) -> Optional[SpeakerInfo]:
        return self._tracker.get_active_speaker()

    def get_stats(self) -> Dict[str, Any]:
        return self._tracker.get_speaker_stats()
