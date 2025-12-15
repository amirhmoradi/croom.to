"""
Video processing pipeline for PiMeet.

Provides frame processing, scaling, and format conversion.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Check for OpenCV
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


@dataclass
class FrameInfo:
    """Metadata about a video frame."""
    width: int
    height: int
    channels: int
    timestamp: datetime
    frame_number: int
    fps: float

    @property
    def resolution(self) -> Tuple[int, int]:
        return (self.width, self.height)

    @property
    def size_bytes(self) -> int:
        return self.width * self.height * self.channels


class VideoProcessor(ABC):
    """Base class for video processors."""

    @abstractmethod
    async def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Process a video frame.

        Args:
            frame: Input frame as numpy array (HWC, BGR)

        Returns:
            Processed frame
        """
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Reset processor state."""
        pass


class ScaleProcessor(VideoProcessor):
    """Scale frames to target resolution."""

    def __init__(
        self,
        target_width: int,
        target_height: int,
        interpolation: int = None
    ):
        self.target_width = target_width
        self.target_height = target_height
        self._interpolation = interpolation or (cv2.INTER_AREA if OPENCV_AVAILABLE else 0)

    async def process(self, frame: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE:
            return frame

        h, w = frame.shape[:2]
        if w == self.target_width and h == self.target_height:
            return frame

        return cv2.resize(
            frame,
            (self.target_width, self.target_height),
            interpolation=self._interpolation
        )

    async def reset(self) -> None:
        pass


class CropProcessor(VideoProcessor):
    """Crop frames to region of interest."""

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    async def process(self, frame: np.ndarray) -> np.ndarray:
        return frame[
            self.y:self.y + self.height,
            self.x:self.x + self.width
        ]

    async def reset(self) -> None:
        pass


class FlipProcessor(VideoProcessor):
    """Flip frames horizontally or vertically."""

    def __init__(self, horizontal: bool = True, vertical: bool = False):
        self.horizontal = horizontal
        self.vertical = vertical

    async def process(self, frame: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE:
            return frame

        if self.horizontal and self.vertical:
            return cv2.flip(frame, -1)
        elif self.horizontal:
            return cv2.flip(frame, 1)
        elif self.vertical:
            return cv2.flip(frame, 0)
        return frame

    async def reset(self) -> None:
        pass


class RotateProcessor(VideoProcessor):
    """Rotate frames by 90, 180, or 270 degrees."""

    def __init__(self, angle: int = 0):
        """
        Args:
            angle: Rotation angle (0, 90, 180, 270)
        """
        self.angle = angle % 360

    async def process(self, frame: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE or self.angle == 0:
            return frame

        if self.angle == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.angle == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif self.angle == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame

    async def reset(self) -> None:
        pass


class ColorConversionProcessor(VideoProcessor):
    """Convert between color spaces."""

    def __init__(self, conversion: int):
        """
        Args:
            conversion: OpenCV color conversion code (e.g., cv2.COLOR_BGR2RGB)
        """
        self.conversion = conversion

    async def process(self, frame: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE:
            return frame
        return cv2.cvtColor(frame, self.conversion)

    async def reset(self) -> None:
        pass


class BrightnessContrastProcessor(VideoProcessor):
    """Adjust brightness and contrast."""

    def __init__(self, brightness: float = 0, contrast: float = 1.0):
        """
        Args:
            brightness: Brightness adjustment (-100 to 100)
            contrast: Contrast multiplier (0.5 to 2.0)
        """
        self.brightness = brightness
        self.contrast = contrast

    async def process(self, frame: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE:
            return frame

        # Apply contrast and brightness
        result = cv2.convertScaleAbs(
            frame,
            alpha=self.contrast,
            beta=self.brightness
        )
        return result

    async def reset(self) -> None:
        pass


class DenoiseProcessor(VideoProcessor):
    """Apply noise reduction to frames."""

    def __init__(self, strength: int = 10):
        """
        Args:
            strength: Denoising strength (1-30)
        """
        self.strength = strength

    async def process(self, frame: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE:
            return frame

        # Use fast denoising for real-time
        return cv2.fastNlMeansDenoisingColored(
            frame,
            None,
            self.strength,
            self.strength,
            7,
            21
        )

    async def reset(self) -> None:
        pass


class BackgroundBlurProcessor(VideoProcessor):
    """
    Apply background blur (virtual background effect).

    Requires segmentation mask from AI service.
    """

    def __init__(self, blur_strength: int = 21):
        """
        Args:
            blur_strength: Blur kernel size (odd number)
        """
        self.blur_strength = blur_strength | 1  # Ensure odd
        self._mask: Optional[np.ndarray] = None

    def set_mask(self, mask: np.ndarray) -> None:
        """
        Set segmentation mask.

        Args:
            mask: Binary mask (255 for foreground, 0 for background)
        """
        self._mask = mask

    async def process(self, frame: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE or self._mask is None:
            return frame

        try:
            # Resize mask if needed
            if self._mask.shape[:2] != frame.shape[:2]:
                mask = cv2.resize(
                    self._mask,
                    (frame.shape[1], frame.shape[0])
                )
            else:
                mask = self._mask

            # Blur background
            blurred = cv2.GaussianBlur(
                frame,
                (self.blur_strength, self.blur_strength),
                0
            )

            # Combine foreground and blurred background
            mask_3ch = np.stack([mask] * 3, axis=-1)
            result = np.where(mask_3ch > 127, frame, blurred)

            return result.astype(np.uint8)

        except Exception as e:
            logger.error(f"Background blur error: {e}")
            return frame

    async def reset(self) -> None:
        self._mask = None


class OverlayProcessor(VideoProcessor):
    """Overlay images or text on frames."""

    def __init__(self):
        self._overlays: List[Dict[str, Any]] = []

    def add_image(
        self,
        image: np.ndarray,
        x: int,
        y: int,
        alpha: float = 1.0,
        name: str = ""
    ) -> None:
        """Add image overlay."""
        self._overlays.append({
            "type": "image",
            "data": image,
            "x": x,
            "y": y,
            "alpha": alpha,
            "name": name,
        })

    def add_text(
        self,
        text: str,
        x: int,
        y: int,
        font_scale: float = 1.0,
        color: Tuple[int, int, int] = (255, 255, 255),
        thickness: int = 2,
        name: str = ""
    ) -> None:
        """Add text overlay."""
        self._overlays.append({
            "type": "text",
            "text": text,
            "x": x,
            "y": y,
            "font_scale": font_scale,
            "color": color,
            "thickness": thickness,
            "name": name,
        })

    def remove_overlay(self, name: str) -> None:
        """Remove overlay by name."""
        self._overlays = [o for o in self._overlays if o.get("name") != name]

    def clear_overlays(self) -> None:
        """Remove all overlays."""
        self._overlays.clear()

    async def process(self, frame: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE or not self._overlays:
            return frame

        result = frame.copy()

        for overlay in self._overlays:
            try:
                if overlay["type"] == "image":
                    img = overlay["data"]
                    x, y = overlay["x"], overlay["y"]
                    alpha = overlay["alpha"]

                    h, w = img.shape[:2]
                    fh, fw = frame.shape[:2]

                    # Clip to frame bounds
                    x2, y2 = min(x + w, fw), min(y + h, fh)
                    x, y = max(0, x), max(0, y)
                    img = img[:y2-y, :x2-x]

                    if alpha < 1.0:
                        result[y:y2, x:x2] = cv2.addWeighted(
                            result[y:y2, x:x2], 1 - alpha,
                            img, alpha, 0
                        )
                    else:
                        result[y:y2, x:x2] = img

                elif overlay["type"] == "text":
                    cv2.putText(
                        result,
                        overlay["text"],
                        (overlay["x"], overlay["y"]),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        overlay["font_scale"],
                        overlay["color"],
                        overlay["thickness"],
                    )

            except Exception as e:
                logger.error(f"Overlay error: {e}")

        return result

    async def reset(self) -> None:
        self._overlays.clear()


class VideoProcessingPipeline:
    """
    Complete video processing pipeline.

    Chains multiple processors together.
    """

    def __init__(self):
        self._processors: List[VideoProcessor] = []
        self._frame_count = 0
        self._fps_history: List[float] = []
        self._last_frame_time: Optional[datetime] = None

    def add_processor(self, processor: VideoProcessor) -> None:
        """Add a processor to the pipeline."""
        self._processors.append(processor)

    def remove_processor(self, processor: VideoProcessor) -> None:
        """Remove a processor from the pipeline."""
        if processor in self._processors:
            self._processors.remove(processor)

    def clear_processors(self) -> None:
        """Remove all processors."""
        self._processors.clear()

    async def process(self, frame: np.ndarray) -> Tuple[np.ndarray, FrameInfo]:
        """
        Process frame through all processors.

        Returns:
            Tuple of (processed frame, frame info)
        """
        result = frame
        now = datetime.now()

        # Calculate FPS
        if self._last_frame_time:
            dt = (now - self._last_frame_time).total_seconds()
            if dt > 0:
                fps = 1.0 / dt
                self._fps_history.append(fps)
                if len(self._fps_history) > 30:
                    self._fps_history.pop(0)

        self._last_frame_time = now

        # Process through pipeline
        for processor in self._processors:
            result = await processor.process(result)

        self._frame_count += 1

        # Create frame info
        h, w = result.shape[:2]
        channels = result.shape[2] if len(result.shape) > 2 else 1
        avg_fps = sum(self._fps_history) / len(self._fps_history) if self._fps_history else 0

        info = FrameInfo(
            width=w,
            height=h,
            channels=channels,
            timestamp=now,
            frame_number=self._frame_count,
            fps=avg_fps,
        )

        return result, info

    async def reset(self) -> None:
        """Reset all processors."""
        for processor in self._processors:
            await processor.reset()
        self._frame_count = 0
        self._fps_history.clear()
        self._last_frame_time = None

    @property
    def fps(self) -> float:
        """Current average FPS."""
        return sum(self._fps_history) / len(self._fps_history) if self._fps_history else 0

    @property
    def frame_count(self) -> int:
        """Total frames processed."""
        return self._frame_count
