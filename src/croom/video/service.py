"""
Video Service for Croom.

High-level video management with camera handling and processing.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable, Tuple
import numpy as np

from croom.video.camera import (
    Camera,
    CameraInfo,
    CameraBackend,
    Resolution,
    RESOLUTION_1080P,
    RESOLUTION_720P,
    get_cameras,
    create_camera,
)
from croom.video.processor import (
    VideoProcessingPipeline,
    VideoProcessor,
    FrameInfo,
    ScaleProcessor,
    FlipProcessor,
    RotateProcessor,
    BackgroundBlurProcessor,
)

logger = logging.getLogger(__name__)


class VideoService:
    """
    High-level video service for Croom.

    Manages cameras, processing pipeline, and frame routing.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize video service.

        Args:
            config: Service configuration with:
                - camera: Camera ID or 'default'
                - resolution: Target resolution string (e.g., '1920x1080')
                - fps: Target frame rate (default 30)
                - mirror: Mirror video horizontally (default True)
                - rotation: Rotation angle (0, 90, 180, 270)
                - background_blur: Enable background blur (default False)
        """
        self.config = config or {}

        # Camera
        self._camera: Optional[Camera] = None
        self._available_cameras: List[CameraInfo] = []

        # Processing
        self._pipeline: Optional[VideoProcessingPipeline] = None
        self._background_blur: Optional[BackgroundBlurProcessor] = None

        # State
        self._running = False
        self._paused = False
        self._resolution: Resolution = RESOLUTION_1080P
        self._fps: int = 30

        # Callbacks
        self._on_frame: List[Callable[[np.ndarray, FrameInfo], None]] = []

        # Frame capture
        self._capture_task: Optional[asyncio.Task] = None
        self._last_frame: Optional[np.ndarray] = None
        self._last_frame_info: Optional[FrameInfo] = None

    async def initialize(self) -> bool:
        """
        Initialize the video service.

        Returns:
            True if initialization successful
        """
        try:
            # Discover cameras
            self._available_cameras = get_cameras()
            logger.info(f"Found {len(self._available_cameras)} cameras")

            # Parse config
            resolution_str = self.config.get('resolution', '1920x1080')
            try:
                self._resolution = Resolution.from_string(resolution_str)
            except Exception:
                self._resolution = RESOLUTION_1080P

            self._fps = self.config.get('fps', 30)

            # Setup camera
            camera_id = self.config.get('camera', 'default')
            if not await self._setup_camera(camera_id):
                logger.warning("No camera configured")

            # Initialize pipeline
            self._pipeline = VideoProcessingPipeline()

            # Add mirror processor if configured
            if self.config.get('mirror', True):
                self._pipeline.add_processor(FlipProcessor(horizontal=True))

            # Add rotation if configured
            rotation = self.config.get('rotation', 0)
            if rotation:
                self._pipeline.add_processor(RotateProcessor(rotation))

            # Add background blur if configured
            if self.config.get('background_blur', False):
                self._background_blur = BackgroundBlurProcessor(
                    blur_strength=self.config.get('blur_strength', 21)
                )
                self._pipeline.add_processor(self._background_blur)

            logger.info("Video service initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize video service: {e}")
            return False

    async def _setup_camera(self, camera_id: str) -> bool:
        """Setup camera device."""
        try:
            camera_info = self._find_camera(camera_id)
            if not camera_info:
                return False

            self._camera = create_camera(camera_info)

            if not await self._camera.open():
                logger.error(f"Failed to open camera: {camera_info.name}")
                return False

            # Set resolution and FPS
            await self._camera.set_resolution(self._resolution)
            await self._camera.set_fps(self._fps)

            logger.info(f"Camera: {camera_info.name} @ {self._resolution}")
            return True

        except Exception as e:
            logger.error(f"Failed to setup camera: {e}")
            return False

    def _find_camera(self, camera_id: str) -> Optional[CameraInfo]:
        """Find camera by ID or return default."""
        if not self._available_cameras:
            return None

        # Prefer Pi camera for 'default'
        if camera_id == 'default':
            pi_camera = next(
                (c for c in self._available_cameras if c.is_pi_camera),
                None
            )
            return pi_camera or self._available_cameras[0]

        # Find by ID
        for camera in self._available_cameras:
            if camera.id == camera_id:
                return camera

        # Fallback to first camera
        return self._available_cameras[0] if self._available_cameras else None

    async def start(self) -> None:
        """Start video capture and processing."""
        if self._running:
            return

        self._running = True

        # Start camera
        if self._camera:
            await self._camera.start()
            self._capture_task = asyncio.create_task(self._capture_loop())

        logger.info("Video service started")

    async def stop(self) -> None:
        """Stop video capture and processing."""
        if not self._running:
            return

        self._running = False

        # Stop capture task
        if self._capture_task:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
            self._capture_task = None

        # Stop camera
        if self._camera:
            await self._camera.stop()

        logger.info("Video service stopped")

    async def _capture_loop(self) -> None:
        """Main video capture and processing loop."""
        while self._running:
            try:
                if self._paused:
                    await asyncio.sleep(0.1)
                    continue

                # Read frame from camera
                frame = await self._camera.read()
                if frame is None:
                    await asyncio.sleep(0.01)
                    continue

                # Process frame
                if self._pipeline:
                    processed, info = await self._pipeline.process(frame)
                else:
                    processed = frame
                    info = None

                self._last_frame = processed
                self._last_frame_info = info

                # Notify listeners
                for callback in self._on_frame:
                    try:
                        callback(processed, info)
                    except Exception as e:
                        logger.error(f"Frame callback error: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Capture loop error: {e}")
                await asyncio.sleep(0.1)

    def pause(self) -> None:
        """Pause video capture (camera stays open)."""
        self._paused = True
        logger.debug("Video paused")

    def resume(self) -> None:
        """Resume video capture."""
        self._paused = False
        logger.debug("Video resumed")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def resolution(self) -> Resolution:
        return self._resolution

    @property
    def fps(self) -> float:
        """Current frame rate."""
        return self._pipeline.fps if self._pipeline else 0

    @property
    def cameras(self) -> List[CameraInfo]:
        """Get list of available cameras."""
        return self._available_cameras.copy()

    @property
    def current_frame(self) -> Optional[np.ndarray]:
        """Get the most recent frame."""
        return self._last_frame

    @property
    def frame_info(self) -> Optional[FrameInfo]:
        """Get info about the most recent frame."""
        return self._last_frame_info

    async def set_resolution(self, resolution: Resolution) -> bool:
        """
        Change video resolution.

        Args:
            resolution: New resolution

        Returns:
            True if change successful
        """
        try:
            self._resolution = resolution

            if self._camera:
                return await self._camera.set_resolution(resolution)

            return True

        except Exception as e:
            logger.error(f"Failed to set resolution: {e}")
            return False

    async def set_fps(self, fps: int) -> bool:
        """
        Change frame rate.

        Args:
            fps: New frame rate

        Returns:
            True if change successful
        """
        try:
            self._fps = fps

            if self._camera:
                return await self._camera.set_fps(fps)

            return True

        except Exception as e:
            logger.error(f"Failed to set FPS: {e}")
            return False

    async def set_camera(self, camera_id: str) -> bool:
        """
        Switch to a different camera.

        Args:
            camera_id: Camera ID to switch to

        Returns:
            True if switch successful
        """
        was_running = self._running

        if self._camera:
            await self._camera.stop()
            await self._camera.close()

        if not await self._setup_camera(camera_id):
            return False

        if was_running and self._camera:
            await self._camera.start()

        return True

    def set_background_mask(self, mask: np.ndarray) -> None:
        """
        Set segmentation mask for background blur.

        Args:
            mask: Binary mask (255 for foreground)
        """
        if self._background_blur:
            self._background_blur.set_mask(mask)

    def enable_background_blur(self, enabled: bool = True) -> None:
        """Enable or disable background blur."""
        if enabled and not self._background_blur:
            self._background_blur = BackgroundBlurProcessor()
            if self._pipeline:
                self._pipeline.add_processor(self._background_blur)
        elif not enabled and self._background_blur:
            if self._pipeline:
                self._pipeline.remove_processor(self._background_blur)
            self._background_blur = None

    def add_processor(self, processor: VideoProcessor) -> None:
        """Add a custom processor to the pipeline."""
        if self._pipeline:
            self._pipeline.add_processor(processor)

    def remove_processor(self, processor: VideoProcessor) -> None:
        """Remove a processor from the pipeline."""
        if self._pipeline:
            self._pipeline.remove_processor(processor)

    def on_frame(self, callback: Callable[[np.ndarray, FrameInfo], None]) -> None:
        """Register callback for processed frames."""
        self._on_frame.append(callback)

    async def capture_snapshot(self) -> Optional[np.ndarray]:
        """
        Capture a single snapshot.

        Returns:
            Frame as numpy array or None
        """
        if self._running:
            return self._last_frame

        # Start camera temporarily
        if self._camera:
            await self._camera.start()
            frame = await self._camera.read()
            await self._camera.stop()
            return frame

        return None

    async def shutdown(self) -> None:
        """Shutdown the video service."""
        await self.stop()

        if self._camera:
            await self._camera.close()
            self._camera = None

        if self._pipeline:
            await self._pipeline.reset()
            self._pipeline = None

        self._on_frame.clear()
        self._last_frame = None
        self._last_frame_info = None

        logger.info("Video service shutdown")


def create_video_service(config: Dict[str, Any]) -> VideoService:
    """
    Create a video service from configuration.

    Args:
        config: Video configuration dict

    Returns:
        Configured VideoService instance
    """
    return VideoService(config)
