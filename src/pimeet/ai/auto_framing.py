"""
Auto-framing module for PiMeet.

Provides intelligent camera framing that automatically tracks and frames
meeting participants. Supports smooth transitions and multiple framing modes.
"""

import asyncio
import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class FramingMode(Enum):
    """Auto-framing modes."""
    OFF = "off"
    GROUP = "group"  # Frame all participants
    SPEAKER = "speaker"  # Frame active speaker
    PRESENTER = "presenter"  # Frame presenter/person sharing
    SINGLE = "single"  # Frame single selected person
    SMART = "smart"  # AI-driven mode selection


class TransitionType(Enum):
    """Camera transition types."""
    CUT = "cut"  # Instant transition
    SMOOTH = "smooth"  # Smooth pan/zoom
    CINEMATIC = "cinematic"  # Film-style transition


@dataclass
class BoundingBox:
    """Bounding box for detected person/face."""
    x1: float  # Normalized 0-1
    y1: float
    x2: float
    y2: float
    confidence: float = 1.0
    class_name: str = "person"
    track_id: Optional[int] = None

    @property
    def center(self) -> Tuple[float, float]:
        """Get center point."""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def area(self) -> float:
        """Get area."""
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    def expand(self, padding: float) -> 'BoundingBox':
        """Expand bounding box by padding ratio."""
        width = self.x2 - self.x1
        height = self.y2 - self.y1
        return BoundingBox(
            x1=max(0, self.x1 - width * padding),
            y1=max(0, self.y1 - height * padding),
            x2=min(1, self.x2 + width * padding),
            y2=min(1, self.y2 + height * padding),
            confidence=self.confidence,
            class_name=self.class_name,
            track_id=self.track_id,
        )


@dataclass
class FrameRegion:
    """Region of interest for camera framing."""
    x1: float
    y1: float
    x2: float
    y2: float
    zoom: float = 1.0  # Zoom factor
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    def to_dict(self) -> dict:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "zoom": self.zoom,
            "center": self.center,
        }


class SmoothingFilter:
    """Kalman-like smoothing filter for camera movements."""

    def __init__(
        self,
        smoothing_factor: float = 0.3,
        velocity_factor: float = 0.1,
    ):
        self._smoothing = smoothing_factor
        self._velocity_factor = velocity_factor
        self._position: Optional[Tuple[float, float]] = None
        self._velocity: Tuple[float, float] = (0, 0)
        self._size: Tuple[float, float] = (1.0, 1.0)
        self._size_velocity: Tuple[float, float] = (0, 0)

    def update(self, target_region: FrameRegion) -> FrameRegion:
        """Update filter with new target and return smoothed result."""
        target_center = target_region.center
        target_size = (target_region.width, target_region.height)

        if self._position is None:
            self._position = target_center
            self._size = target_size
            return target_region

        # Calculate velocity
        dx = target_center[0] - self._position[0]
        dy = target_center[1] - self._position[1]

        # Update velocity with smoothing
        self._velocity = (
            self._velocity[0] * (1 - self._velocity_factor) + dx * self._velocity_factor,
            self._velocity[1] * (1 - self._velocity_factor) + dy * self._velocity_factor,
        )

        # Update position
        self._position = (
            self._position[0] + dx * self._smoothing + self._velocity[0] * 0.5,
            self._position[1] + dy * self._smoothing + self._velocity[1] * 0.5,
        )

        # Update size
        dw = target_size[0] - self._size[0]
        dh = target_size[1] - self._size[1]
        self._size = (
            self._size[0] + dw * self._smoothing,
            self._size[1] + dh * self._smoothing,
        )

        # Clamp values
        self._position = (
            max(0, min(1, self._position[0])),
            max(0, min(1, self._position[1])),
        )

        half_w = self._size[0] / 2
        half_h = self._size[1] / 2

        return FrameRegion(
            x1=max(0, self._position[0] - half_w),
            y1=max(0, self._position[1] - half_h),
            x2=min(1, self._position[0] + half_w),
            y2=min(1, self._position[1] + half_h),
            zoom=target_region.zoom,
            confidence=target_region.confidence,
        )

    def reset(self) -> None:
        """Reset filter state."""
        self._position = None
        self._velocity = (0, 0)
        self._size = (1.0, 1.0)
        self._size_velocity = (0, 0)


class PersonTracker:
    """Tracks persons across frames with simple IoU tracking."""

    def __init__(self, max_age: int = 30, min_hits: int = 3):
        self._max_age = max_age
        self._min_hits = min_hits
        self._tracks: Dict[int, Dict[str, Any]] = {}
        self._next_id = 1

    def update(self, detections: List[BoundingBox]) -> List[BoundingBox]:
        """Update tracks with new detections."""
        # Simple IoU matching
        matched = []
        unmatched_detections = list(range(len(detections)))
        unmatched_tracks = list(self._tracks.keys())

        # Calculate IoU matrix
        if self._tracks and detections:
            for det_idx, det in enumerate(detections):
                best_iou = 0.3  # Minimum IoU threshold
                best_track = None

                for track_id in unmatched_tracks:
                    track = self._tracks[track_id]
                    iou = self._calculate_iou(det, track["bbox"])

                    if iou > best_iou:
                        best_iou = iou
                        best_track = track_id

                if best_track is not None:
                    matched.append((det_idx, best_track))
                    unmatched_tracks.remove(best_track)
                    unmatched_detections.remove(det_idx)

        # Update matched tracks
        for det_idx, track_id in matched:
            self._tracks[track_id]["bbox"] = detections[det_idx]
            self._tracks[track_id]["age"] = 0
            self._tracks[track_id]["hits"] += 1
            detections[det_idx].track_id = track_id

        # Create new tracks for unmatched detections
        for det_idx in unmatched_detections:
            track_id = self._next_id
            self._next_id += 1
            self._tracks[track_id] = {
                "bbox": detections[det_idx],
                "age": 0,
                "hits": 1,
            }
            detections[det_idx].track_id = track_id

        # Age unmatched tracks and remove old ones
        for track_id in list(unmatched_tracks):
            self._tracks[track_id]["age"] += 1
            if self._tracks[track_id]["age"] > self._max_age:
                del self._tracks[track_id]

        # Return detections with stable tracks
        return [
            d for d in detections
            if d.track_id in self._tracks and
            self._tracks[d.track_id]["hits"] >= self._min_hits
        ]

    def _calculate_iou(self, box1: BoundingBox, box2: BoundingBox) -> float:
        """Calculate intersection over union."""
        x1 = max(box1.x1, box2.x1)
        y1 = max(box1.y1, box2.y1)
        x2 = min(box1.x2, box2.x2)
        y2 = min(box1.y2, box2.y2)

        if x2 < x1 or y2 < y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        union = box1.area + box2.area - intersection

        return intersection / union if union > 0 else 0.0

    def reset(self) -> None:
        """Reset tracker state."""
        self._tracks.clear()
        self._next_id = 1


class AutoFramingEngine:
    """Main auto-framing engine."""

    def __init__(
        self,
        frame_width: int = 1920,
        frame_height: int = 1080,
        aspect_ratio: float = 16 / 9,
        smoothing: float = 0.2,
        min_person_area: float = 0.01,
        max_zoom: float = 3.0,
    ):
        """
        Initialize auto-framing engine.

        Args:
            frame_width: Input frame width
            frame_height: Input frame height
            aspect_ratio: Output aspect ratio
            smoothing: Smoothing factor (0-1)
            min_person_area: Minimum normalized area for a person
            max_zoom: Maximum zoom factor
        """
        self._frame_width = frame_width
        self._frame_height = frame_height
        self._aspect_ratio = aspect_ratio
        self._min_person_area = min_person_area
        self._max_zoom = max_zoom

        self._mode = FramingMode.GROUP
        self._transition = TransitionType.SMOOTH
        self._enabled = True

        self._tracker = PersonTracker()
        self._smoother = SmoothingFilter(smoothing_factor=smoothing)
        self._current_region: Optional[FrameRegion] = None
        self._target_region: Optional[FrameRegion] = None

        # Mode-specific settings
        self._speaker_id: Optional[int] = None
        self._selected_person_id: Optional[int] = None

        # History for smart mode
        self._detection_history: Deque[List[BoundingBox]] = deque(maxlen=30)
        self._frame_history: Deque[FrameRegion] = deque(maxlen=100)

        # Callbacks
        self._on_region_change: List[Callable[[FrameRegion], None]] = []
        self._on_mode_change: List[Callable[[FramingMode], None]] = []

    @property
    def mode(self) -> FramingMode:
        return self._mode

    @mode.setter
    def mode(self, value: FramingMode) -> None:
        if value != self._mode:
            self._mode = value
            self._emit_mode_change(value)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def current_region(self) -> Optional[FrameRegion]:
        return self._current_region

    def process_detections(
        self,
        person_boxes: List[BoundingBox],
        face_boxes: Optional[List[BoundingBox]] = None,
        speaker_audio_levels: Optional[Dict[int, float]] = None,
    ) -> FrameRegion:
        """
        Process detections and calculate optimal framing region.

        Args:
            person_boxes: Detected person bounding boxes
            face_boxes: Optional face detections for better framing
            speaker_audio_levels: Optional audio levels per person for speaker detection

        Returns:
            Calculated frame region
        """
        if not self._enabled or self._mode == FramingMode.OFF:
            return FrameRegion(x1=0, y1=0, x2=1, y2=1)

        # Track persons across frames
        tracked_persons = self._tracker.update(person_boxes)
        self._detection_history.append(tracked_persons)

        # Filter out small detections
        valid_persons = [
            p for p in tracked_persons
            if p.area >= self._min_person_area
        ]

        # Calculate target region based on mode
        if self._mode == FramingMode.GROUP:
            target = self._calculate_group_frame(valid_persons)
        elif self._mode == FramingMode.SPEAKER:
            target = self._calculate_speaker_frame(valid_persons, speaker_audio_levels)
        elif self._mode == FramingMode.SINGLE:
            target = self._calculate_single_frame(valid_persons)
        elif self._mode == FramingMode.PRESENTER:
            target = self._calculate_presenter_frame(valid_persons)
        elif self._mode == FramingMode.SMART:
            target = self._calculate_smart_frame(valid_persons, speaker_audio_levels)
        else:
            target = FrameRegion(x1=0, y1=0, x2=1, y2=1)

        # Apply aspect ratio constraint
        target = self._apply_aspect_ratio(target)

        # Apply smoothing
        if self._transition == TransitionType.CUT:
            self._current_region = target
        else:
            self._current_region = self._smoother.update(target)

        # Store in history
        self._frame_history.append(self._current_region)

        # Emit change callback
        self._emit_region_change(self._current_region)

        return self._current_region

    def _calculate_group_frame(self, persons: List[BoundingBox]) -> FrameRegion:
        """Calculate frame to include all persons."""
        if not persons:
            return FrameRegion(x1=0, y1=0, x2=1, y2=1)

        # Get bounding box containing all persons
        x1 = min(p.x1 for p in persons)
        y1 = min(p.y1 for p in persons)
        x2 = max(p.x2 for p in persons)
        y2 = max(p.y2 for p in persons)

        # Add padding
        padding = 0.1
        width = x2 - x1
        height = y2 - y1

        x1 = max(0, x1 - width * padding)
        y1 = max(0, y1 - height * padding)
        x2 = min(1, x2 + width * padding)
        y2 = min(1, y2 + height * padding)

        # Calculate zoom
        target_width = x2 - x1
        zoom = 1.0 / target_width if target_width > 0 else 1.0
        zoom = min(zoom, self._max_zoom)

        return FrameRegion(
            x1=x1, y1=y1, x2=x2, y2=y2,
            zoom=zoom,
            confidence=min(p.confidence for p in persons),
        )

    def _calculate_speaker_frame(
        self,
        persons: List[BoundingBox],
        audio_levels: Optional[Dict[int, float]],
    ) -> FrameRegion:
        """Calculate frame focused on active speaker."""
        if not persons:
            return FrameRegion(x1=0, y1=0, x2=1, y2=1)

        speaker = None

        # Find speaker by audio level
        if audio_levels:
            max_level = 0
            for person in persons:
                if person.track_id and person.track_id in audio_levels:
                    level = audio_levels[person.track_id]
                    if level > max_level:
                        max_level = level
                        speaker = person

        # Fall back to previously identified speaker
        if speaker is None and self._speaker_id:
            for person in persons:
                if person.track_id == self._speaker_id:
                    speaker = person
                    break

        # Fall back to largest/closest person
        if speaker is None:
            speaker = max(persons, key=lambda p: p.area)

        # Update speaker ID
        if speaker:
            self._speaker_id = speaker.track_id

        return self._frame_single_person(speaker)

    def _calculate_single_frame(self, persons: List[BoundingBox]) -> FrameRegion:
        """Calculate frame for a specific selected person."""
        target = None

        if self._selected_person_id:
            for person in persons:
                if person.track_id == self._selected_person_id:
                    target = person
                    break

        if target is None and persons:
            target = persons[0]

        return self._frame_single_person(target)

    def _calculate_presenter_frame(self, persons: List[BoundingBox]) -> FrameRegion:
        """Calculate frame for presenter (typically screen-sharing person)."""
        # In absence of explicit presenter info, use largest person
        if not persons:
            return FrameRegion(x1=0, y1=0, x2=1, y2=1)

        presenter = max(persons, key=lambda p: p.area)
        return self._frame_single_person(presenter)

    def _calculate_smart_frame(
        self,
        persons: List[BoundingBox],
        audio_levels: Optional[Dict[int, float]],
    ) -> FrameRegion:
        """AI-driven smart framing mode."""
        if not persons:
            return FrameRegion(x1=0, y1=0, x2=1, y2=1)

        # Single person: focus on them
        if len(persons) == 1:
            return self._frame_single_person(persons[0])

        # Check for active speaker
        if audio_levels:
            max_level = max(audio_levels.values()) if audio_levels else 0
            if max_level > 0.3:  # Significant audio activity
                return self._calculate_speaker_frame(persons, audio_levels)

        # Multiple people, no clear speaker: group frame
        return self._calculate_group_frame(persons)

    def _frame_single_person(self, person: Optional[BoundingBox]) -> FrameRegion:
        """Create frame for a single person."""
        if person is None:
            return FrameRegion(x1=0, y1=0, x2=1, y2=1)

        # Expand bounding box
        expanded = person.expand(0.3)

        # Calculate zoom
        target_width = expanded.x2 - expanded.x1
        zoom = 1.0 / target_width if target_width > 0 else 1.0
        zoom = min(zoom, self._max_zoom)

        return FrameRegion(
            x1=expanded.x1,
            y1=expanded.y1,
            x2=expanded.x2,
            y2=expanded.y2,
            zoom=zoom,
            confidence=person.confidence,
        )

    def _apply_aspect_ratio(self, region: FrameRegion) -> FrameRegion:
        """Adjust region to match target aspect ratio."""
        current_ratio = region.width / region.height if region.height > 0 else 1

        if abs(current_ratio - self._aspect_ratio) < 0.01:
            return region

        center_x, center_y = region.center

        if current_ratio > self._aspect_ratio:
            # Too wide, expand height
            new_height = region.width / self._aspect_ratio
            half_h = new_height / 2
            y1 = max(0, center_y - half_h)
            y2 = min(1, center_y + half_h)
            x1, x2 = region.x1, region.x2
        else:
            # Too tall, expand width
            new_width = region.height * self._aspect_ratio
            half_w = new_width / 2
            x1 = max(0, center_x - half_w)
            x2 = min(1, center_x + half_w)
            y1, y2 = region.y1, region.y2

        return FrameRegion(
            x1=x1, y1=y1, x2=x2, y2=y2,
            zoom=region.zoom,
            confidence=region.confidence,
        )

    def select_person(self, track_id: int) -> None:
        """Select a specific person for SINGLE mode."""
        self._selected_person_id = track_id

    def reset(self) -> None:
        """Reset framing state."""
        self._tracker.reset()
        self._smoother.reset()
        self._current_region = None
        self._target_region = None
        self._speaker_id = None
        self._selected_person_id = None
        self._detection_history.clear()
        self._frame_history.clear()

    # Callbacks
    def on_region_change(self, callback: Callable[[FrameRegion], None]) -> None:
        self._on_region_change.append(callback)

    def on_mode_change(self, callback: Callable[[FramingMode], None]) -> None:
        self._on_mode_change.append(callback)

    def _emit_region_change(self, region: FrameRegion) -> None:
        for callback in self._on_region_change:
            try:
                callback(region)
            except Exception as e:
                logger.error(f"Region change callback error: {e}")

    def _emit_mode_change(self, mode: FramingMode) -> None:
        for callback in self._on_mode_change:
            try:
                callback(mode)
            except Exception as e:
                logger.error(f"Mode change callback error: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "mode": self._mode.value,
            "transition": self._transition.value,
            "current_region": self._current_region.to_dict() if self._current_region else None,
            "tracked_persons": len(self._tracker._tracks),
            "speaker_id": self._speaker_id,
            "selected_person_id": self._selected_person_id,
        }


class AutoFramingService:
    """High-level service for auto-framing integration."""

    def __init__(self, ai_service, video_service):
        self._ai_service = ai_service
        self._video_service = video_service
        self._engine = AutoFramingEngine()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start auto-framing service."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("Auto-framing service started")

    async def stop(self) -> None:
        """Stop auto-framing service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._engine.reset()
        logger.info("Auto-framing service stopped")

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                # Get current frame
                frame = await self._video_service.get_frame()
                if frame is None:
                    await asyncio.sleep(0.033)  # ~30fps
                    continue

                # Run person detection
                result = await self._ai_service.detect_persons(frame)

                # Convert to bounding boxes
                boxes = [
                    BoundingBox(
                        x1=d.bbox[0],
                        y1=d.bbox[1],
                        x2=d.bbox[2],
                        y2=d.bbox[3],
                        confidence=d.confidence,
                        class_name=d.class_name,
                    )
                    for d in result.detections
                ]

                # Process framing
                region = self._engine.process_detections(boxes)

                # Apply to video output
                await self._video_service.set_crop_region(
                    region.x1, region.y1, region.x2, region.y2
                )

            except Exception as e:
                logger.error(f"Auto-framing error: {e}")

            await asyncio.sleep(0.033)  # ~30fps

    @property
    def engine(self) -> AutoFramingEngine:
        return self._engine

    def set_mode(self, mode: FramingMode) -> None:
        self._engine.mode = mode

    def set_enabled(self, enabled: bool) -> None:
        self._engine.enabled = enabled
