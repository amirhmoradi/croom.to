"""
Gesture Recognition for Croom.

Provides computer vision-based gesture recognition for
touchless meeting controls.

Supported gestures:
- Wave (start/stop meeting)
- Thumbs up/down (reactions)
- Raised hand
- Peace sign (leave meeting)
- Open palm (mute/unmute)
- Pinch zoom
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class GestureType(Enum):
    """Supported gesture types."""
    NONE = "none"
    WAVE = "wave"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RAISED_HAND = "raised_hand"
    PEACE_SIGN = "peace_sign"
    OPEN_PALM = "open_palm"
    CLOSED_FIST = "closed_fist"
    POINTING = "pointing"
    PINCH = "pinch"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"


class GestureAction(Enum):
    """Actions triggered by gestures."""
    START_MEETING = "start_meeting"
    END_MEETING = "end_meeting"
    TOGGLE_MUTE = "toggle_mute"
    TOGGLE_CAMERA = "toggle_camera"
    RAISE_HAND = "raise_hand"
    REACT_THUMBS_UP = "react_thumbs_up"
    REACT_THUMBS_DOWN = "react_thumbs_down"
    LEAVE_MEETING = "leave_meeting"
    NEXT_LAYOUT = "next_layout"
    PREVIOUS_LAYOUT = "previous_layout"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


@dataclass
class HandLandmarks:
    """Hand landmark positions (21 points per hand)."""
    # Finger tip indices
    WRIST = 0
    THUMB_TIP = 4
    INDEX_TIP = 8
    MIDDLE_TIP = 12
    RING_TIP = 16
    PINKY_TIP = 20

    landmarks: np.ndarray  # Shape: (21, 3) for x, y, z
    handedness: str = "right"  # "left" or "right"
    confidence: float = 0.0

    def get_finger_tips(self) -> np.ndarray:
        """Get finger tip positions."""
        return self.landmarks[[4, 8, 12, 16, 20]]

    def get_finger_mcps(self) -> np.ndarray:
        """Get finger MCP (base) positions."""
        return self.landmarks[[2, 5, 9, 13, 17]]

    def is_finger_extended(self, finger_idx: int) -> bool:
        """Check if a finger is extended."""
        # Finger indices: 0=thumb, 1=index, 2=middle, 3=ring, 4=pinky
        tip_idx = [4, 8, 12, 16, 20][finger_idx]
        pip_idx = [3, 6, 10, 14, 18][finger_idx]

        if finger_idx == 0:  # Thumb
            return self.landmarks[tip_idx][0] > self.landmarks[pip_idx][0]
        else:
            return self.landmarks[tip_idx][1] < self.landmarks[pip_idx][1]

    def count_extended_fingers(self) -> int:
        """Count number of extended fingers."""
        count = 0
        for i in range(5):
            if self.is_finger_extended(i):
                count += 1
        return count


@dataclass
class GestureEvent:
    """Detected gesture event."""
    gesture: GestureType
    confidence: float
    hand: str  # "left", "right", or "both"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration: float = 0.0  # How long the gesture was held
    position: Tuple[float, float] = (0.5, 0.5)  # Normalized position
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GestureConfig:
    """Gesture recognition configuration."""
    enabled: bool = True
    min_confidence: float = 0.7
    min_detection_frames: int = 5
    gesture_cooldown: float = 1.0  # Seconds between same gesture
    wave_min_oscillations: int = 2
    pinch_threshold: float = 0.05
    swipe_min_distance: float = 0.2
    swipe_max_duration: float = 0.5


class GestureClassifier:
    """
    Classifies hand landmarks into gesture types.
    """

    def __init__(self, config: GestureConfig = None):
        self._config = config or GestureConfig()
        self._gesture_history: List[Tuple[GestureType, float]] = []
        self._wave_positions: List[float] = []
        self._last_gesture: Optional[GestureType] = None
        self._last_gesture_time: float = 0

    def classify(self, hands: List[HandLandmarks]) -> Optional[GestureEvent]:
        """
        Classify hand landmarks into a gesture.

        Args:
            hands: List of detected hands with landmarks

        Returns:
            Detected gesture event or None
        """
        if not hands:
            self._wave_positions.clear()
            return None

        # Get primary hand (right preferred)
        primary = None
        for hand in hands:
            if hand.handedness == "right":
                primary = hand
                break
        if not primary:
            primary = hands[0]

        # Check for two-hand gestures first
        if len(hands) >= 2:
            gesture = self._classify_two_hand(hands)
            if gesture:
                return gesture

        # Classify single hand gesture
        return self._classify_single_hand(primary)

    def _classify_single_hand(self, hand: HandLandmarks) -> Optional[GestureEvent]:
        """Classify single hand gesture."""
        extended = [hand.is_finger_extended(i) for i in range(5)]
        extended_count = sum(extended)

        gesture = GestureType.NONE
        confidence = 0.8

        # Open palm - all fingers extended
        if all(extended):
            gesture = GestureType.OPEN_PALM
            confidence = 0.9

        # Closed fist - no fingers extended
        elif extended_count == 0:
            gesture = GestureType.CLOSED_FIST
            confidence = 0.85

        # Thumbs up - only thumb extended, hand orientation check
        elif extended[0] and not any(extended[1:]):
            thumb_tip = hand.landmarks[4]
            wrist = hand.landmarks[0]
            if thumb_tip[1] < wrist[1]:  # Thumb above wrist
                gesture = GestureType.THUMBS_UP
                confidence = 0.85

        # Thumbs down
        elif extended[0] and not any(extended[1:]):
            thumb_tip = hand.landmarks[4]
            wrist = hand.landmarks[0]
            if thumb_tip[1] > wrist[1]:  # Thumb below wrist
                gesture = GestureType.THUMBS_DOWN
                confidence = 0.85

        # Peace sign - index and middle extended
        elif extended[1] and extended[2] and not extended[3] and not extended[4]:
            gesture = GestureType.PEACE_SIGN
            confidence = 0.85

        # Pointing - only index extended
        elif extended[1] and not any([extended[0], extended[2], extended[3], extended[4]]):
            gesture = GestureType.POINTING
            confidence = 0.8

        # Raised hand - all fingers extended, palm facing camera
        elif all(extended) and self._is_palm_facing(hand):
            gesture = GestureType.RAISED_HAND
            confidence = 0.9

        # Check for wave gesture (requires motion tracking)
        wave_gesture = self._detect_wave(hand)
        if wave_gesture:
            return wave_gesture

        if gesture == GestureType.NONE:
            return None

        # Apply cooldown
        current_time = time.time()
        if (gesture == self._last_gesture and
            current_time - self._last_gesture_time < self._config.gesture_cooldown):
            return None

        if confidence >= self._config.min_confidence:
            self._last_gesture = gesture
            self._last_gesture_time = current_time

            return GestureEvent(
                gesture=gesture,
                confidence=confidence,
                hand=hand.handedness,
                position=(
                    float(hand.landmarks[0][0]),
                    float(hand.landmarks[0][1])
                ),
            )

        return None

    def _classify_two_hand(self, hands: List[HandLandmarks]) -> Optional[GestureEvent]:
        """Classify two-hand gestures."""
        if len(hands) < 2:
            return None

        # Sort by handedness
        left_hand = None
        right_hand = None

        for hand in hands:
            if hand.handedness == "left":
                left_hand = hand
            else:
                right_hand = hand

        if not left_hand or not right_hand:
            return None

        # Pinch detection (thumb and index close together on both hands)
        left_pinch = self._get_pinch_distance(left_hand)
        right_pinch = self._get_pinch_distance(right_hand)

        if left_pinch < self._config.pinch_threshold and right_pinch < self._config.pinch_threshold:
            # Calculate zoom based on hand distance
            hand_distance = np.linalg.norm(
                left_hand.landmarks[0] - right_hand.landmarks[0]
            )

            return GestureEvent(
                gesture=GestureType.PINCH,
                confidence=0.85,
                hand="both",
                metadata={"hand_distance": float(hand_distance)},
            )

        return None

    def _detect_wave(self, hand: HandLandmarks) -> Optional[GestureEvent]:
        """Detect wave gesture from motion."""
        # Track horizontal position of hand
        x_pos = hand.landmarks[0][0]
        self._wave_positions.append(x_pos)

        # Keep only recent positions
        if len(self._wave_positions) > 30:
            self._wave_positions.pop(0)

        if len(self._wave_positions) < 10:
            return None

        # Detect oscillation (direction changes)
        oscillations = 0
        last_direction = None

        for i in range(1, len(self._wave_positions)):
            diff = self._wave_positions[i] - self._wave_positions[i - 1]
            if abs(diff) > 0.01:
                direction = 1 if diff > 0 else -1
                if last_direction is not None and direction != last_direction:
                    oscillations += 1
                last_direction = direction

        if oscillations >= self._config.wave_min_oscillations:
            self._wave_positions.clear()

            # Check cooldown
            current_time = time.time()
            if (GestureType.WAVE == self._last_gesture and
                current_time - self._last_gesture_time < self._config.gesture_cooldown):
                return None

            self._last_gesture = GestureType.WAVE
            self._last_gesture_time = current_time

            return GestureEvent(
                gesture=GestureType.WAVE,
                confidence=0.85,
                hand=hand.handedness,
            )

        return None

    def _is_palm_facing(self, hand: HandLandmarks) -> bool:
        """Check if palm is facing the camera."""
        # Use cross product of finger vectors to determine palm orientation
        index_base = hand.landmarks[5]
        pinky_base = hand.landmarks[17]
        wrist = hand.landmarks[0]

        v1 = index_base - wrist
        v2 = pinky_base - wrist

        # Simplified check - if z component suggests palm facing camera
        return True  # Placeholder - full implementation needs depth

    def _get_pinch_distance(self, hand: HandLandmarks) -> float:
        """Get distance between thumb and index finger tips."""
        thumb_tip = hand.landmarks[4]
        index_tip = hand.landmarks[8]
        return float(np.linalg.norm(thumb_tip - index_tip))


class GestureActionMapper:
    """
    Maps gestures to actions.
    """

    DEFAULT_MAPPINGS = {
        GestureType.WAVE: GestureAction.START_MEETING,
        GestureType.THUMBS_UP: GestureAction.REACT_THUMBS_UP,
        GestureType.THUMBS_DOWN: GestureAction.REACT_THUMBS_DOWN,
        GestureType.RAISED_HAND: GestureAction.RAISE_HAND,
        GestureType.PEACE_SIGN: GestureAction.LEAVE_MEETING,
        GestureType.OPEN_PALM: GestureAction.TOGGLE_MUTE,
        GestureType.CLOSED_FIST: GestureAction.TOGGLE_CAMERA,
        GestureType.SWIPE_LEFT: GestureAction.PREVIOUS_LAYOUT,
        GestureType.SWIPE_RIGHT: GestureAction.NEXT_LAYOUT,
        GestureType.PINCH: GestureAction.ZOOM_IN,
    }

    def __init__(self, mappings: Dict[GestureType, GestureAction] = None):
        self._mappings = mappings or self.DEFAULT_MAPPINGS.copy()

    def get_action(self, gesture: GestureType) -> Optional[GestureAction]:
        """Get action for a gesture."""
        return self._mappings.get(gesture)

    def set_mapping(self, gesture: GestureType, action: GestureAction) -> None:
        """Set gesture to action mapping."""
        self._mappings[gesture] = action

    def remove_mapping(self, gesture: GestureType) -> None:
        """Remove gesture mapping."""
        if gesture in self._mappings:
            del self._mappings[gesture]


class GestureRecognitionService:
    """
    Gesture recognition service for Croom.

    Integrates with AI backend for hand detection and provides
    gesture-based meeting controls.
    """

    def __init__(
        self,
        config: GestureConfig = None,
        action_mapper: GestureActionMapper = None,
    ):
        self._config = config or GestureConfig()
        self._classifier = GestureClassifier(self._config)
        self._action_mapper = action_mapper or GestureActionMapper()

        self._running = False
        self._enabled = self._config.enabled
        self._ai_backend = None
        self._camera_source = None

        self._action_callbacks: Dict[GestureAction, List[Callable]] = {}
        self._gesture_callbacks: List[Callable] = []

        self._detection_buffer: List[GestureType] = []
        self._last_action_time: Dict[GestureAction, float] = {}

    async def start(self, ai_backend=None, camera_source=None) -> bool:
        """Start gesture recognition service."""
        self._ai_backend = ai_backend
        self._camera_source = camera_source

        if not self._ai_backend:
            logger.warning("No AI backend provided for gesture recognition")
            return False

        self._running = True
        asyncio.create_task(self._recognition_loop())

        logger.info("Gesture recognition service started")
        return True

    async def stop(self) -> None:
        """Stop gesture recognition service."""
        self._running = False
        logger.info("Gesture recognition service stopped")

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable gesture recognition."""
        self._enabled = enabled
        logger.info(f"Gesture recognition {'enabled' if enabled else 'disabled'}")

    def is_enabled(self) -> bool:
        """Check if gesture recognition is enabled."""
        return self._enabled

    def add_action_callback(
        self,
        action: GestureAction,
        callback: Callable[[GestureAction, GestureEvent], None]
    ) -> None:
        """Add callback for specific action."""
        if action not in self._action_callbacks:
            self._action_callbacks[action] = []
        self._action_callbacks[action].append(callback)

    def add_gesture_callback(
        self,
        callback: Callable[[GestureEvent], None]
    ) -> None:
        """Add callback for all gestures."""
        self._gesture_callbacks.append(callback)

    async def _recognition_loop(self) -> None:
        """Main recognition loop."""
        while self._running:
            if not self._enabled:
                await asyncio.sleep(0.1)
                continue

            try:
                # Get frame from camera
                if self._camera_source:
                    frame = await self._camera_source.get_frame()
                else:
                    await asyncio.sleep(0.033)
                    continue

                # Detect hands using AI backend
                hands = await self._detect_hands(frame)

                # Classify gesture
                gesture_event = self._classifier.classify(hands)

                if gesture_event:
                    # Add to detection buffer for stability
                    self._detection_buffer.append(gesture_event.gesture)

                    if len(self._detection_buffer) > self._config.min_detection_frames:
                        self._detection_buffer.pop(0)

                    # Check if gesture is stable
                    if self._is_gesture_stable(gesture_event.gesture):
                        await self._handle_gesture(gesture_event)
                        self._detection_buffer.clear()

            except Exception as e:
                logger.error(f"Error in gesture recognition: {e}")

            await asyncio.sleep(0.033)  # ~30 FPS

    async def _detect_hands(self, frame: np.ndarray) -> List[HandLandmarks]:
        """Detect hands in frame using AI backend."""
        if not self._ai_backend:
            return []

        try:
            # Call AI backend for hand detection
            results = await self._ai_backend.detect_hands(frame)

            hands = []
            for result in results:
                landmarks = np.array(result.get("landmarks", []))
                if len(landmarks) == 21:
                    hands.append(HandLandmarks(
                        landmarks=landmarks,
                        handedness=result.get("handedness", "right"),
                        confidence=result.get("confidence", 0.0),
                    ))

            return hands

        except Exception as e:
            logger.debug(f"Hand detection error: {e}")
            return []

    def _is_gesture_stable(self, gesture: GestureType) -> bool:
        """Check if gesture has been stable for required frames."""
        if len(self._detection_buffer) < self._config.min_detection_frames:
            return False

        # Check if all recent detections are the same gesture
        return all(g == gesture for g in self._detection_buffer[-self._config.min_detection_frames:])

    async def _handle_gesture(self, event: GestureEvent) -> None:
        """Handle detected gesture."""
        # Get action for gesture
        action = self._action_mapper.get_action(event.gesture)

        # Notify gesture callbacks
        for callback in self._gesture_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in gesture callback: {e}")

        if action:
            # Check action cooldown
            current_time = time.time()
            last_time = self._last_action_time.get(action, 0)

            if current_time - last_time < self._config.gesture_cooldown:
                return

            self._last_action_time[action] = current_time

            # Notify action callbacks
            if action in self._action_callbacks:
                for callback in self._action_callbacks[action]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(action, event)
                        else:
                            callback(action, event)
                    except Exception as e:
                        logger.error(f"Error in action callback: {e}")

            logger.info(f"Gesture action: {action.value} from {event.gesture.value}")


class GestureMeetingController:
    """
    Controls meeting functions via gestures.
    """

    def __init__(
        self,
        gesture_service: GestureRecognitionService,
        meeting_service=None
    ):
        self._gesture_service = gesture_service
        self._meeting_service = meeting_service
        self._enabled = True

        # Register action handlers
        self._gesture_service.add_action_callback(
            GestureAction.TOGGLE_MUTE, self._on_toggle_mute
        )
        self._gesture_service.add_action_callback(
            GestureAction.TOGGLE_CAMERA, self._on_toggle_camera
        )
        self._gesture_service.add_action_callback(
            GestureAction.RAISE_HAND, self._on_raise_hand
        )
        self._gesture_service.add_action_callback(
            GestureAction.REACT_THUMBS_UP, self._on_react
        )
        self._gesture_service.add_action_callback(
            GestureAction.REACT_THUMBS_DOWN, self._on_react
        )
        self._gesture_service.add_action_callback(
            GestureAction.LEAVE_MEETING, self._on_leave_meeting
        )
        self._gesture_service.add_action_callback(
            GestureAction.START_MEETING, self._on_start_meeting
        )

    def set_meeting_service(self, meeting_service) -> None:
        """Set meeting service."""
        self._meeting_service = meeting_service

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable gesture controls."""
        self._enabled = enabled

    async def _on_toggle_mute(self, action: GestureAction, event: GestureEvent) -> None:
        if self._enabled and self._meeting_service:
            await self._meeting_service.toggle_mute()
            logger.info("Gesture: Toggled mute")

    async def _on_toggle_camera(self, action: GestureAction, event: GestureEvent) -> None:
        if self._enabled and self._meeting_service:
            await self._meeting_service.toggle_camera()
            logger.info("Gesture: Toggled camera")

    async def _on_raise_hand(self, action: GestureAction, event: GestureEvent) -> None:
        if self._enabled and self._meeting_service:
            await self._meeting_service.raise_hand()
            logger.info("Gesture: Raised hand")

    async def _on_react(self, action: GestureAction, event: GestureEvent) -> None:
        if self._enabled and self._meeting_service:
            reaction = "thumbs_up" if action == GestureAction.REACT_THUMBS_UP else "thumbs_down"
            await self._meeting_service.send_reaction(reaction)
            logger.info(f"Gesture: Sent {reaction} reaction")

    async def _on_leave_meeting(self, action: GestureAction, event: GestureEvent) -> None:
        if self._enabled and self._meeting_service:
            await self._meeting_service.leave_meeting()
            logger.info("Gesture: Left meeting")

    async def _on_start_meeting(self, action: GestureAction, event: GestureEvent) -> None:
        if self._enabled and self._meeting_service:
            # Could trigger quick join or scheduled meeting
            logger.info("Gesture: Wave detected - ready to start meeting")
