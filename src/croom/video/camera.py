"""
Camera abstraction for Croom.

Provides unified interface for different camera backends:
- libcamera (Pi Camera Module, recommended on Pi 5)
- v4l2 (USB webcams, generic Linux)
- OpenCV (fallback, cross-platform)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Tuple
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class CameraBackend(Enum):
    """Available camera backends."""
    LIBCAMERA = "libcamera"    # Pi Camera Module (recommended)
    V4L2 = "v4l2"              # Video4Linux2 (USB webcams)
    OPENCV = "opencv"          # OpenCV fallback
    AUTO = "auto"              # Auto-detect best backend


@dataclass
class Resolution:
    """Video resolution."""
    width: int
    height: int

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height > 0 else 0

    @property
    def pixels(self) -> int:
        return self.width * self.height

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"

    @classmethod
    def from_string(cls, s: str) -> "Resolution":
        """Parse resolution from string like '1920x1080'."""
        w, h = s.lower().split("x")
        return cls(int(w), int(h))


# Common resolutions
RESOLUTION_4K = Resolution(3840, 2160)
RESOLUTION_1080P = Resolution(1920, 1080)
RESOLUTION_720P = Resolution(1280, 720)
RESOLUTION_480P = Resolution(640, 480)
RESOLUTION_360P = Resolution(480, 360)


@dataclass
class CameraInfo:
    """Information about a camera device."""
    id: str
    name: str
    backend: CameraBackend
    device_path: str = ""
    resolutions: List[Resolution] = field(default_factory=list)
    max_fps: int = 30
    has_autofocus: bool = False
    has_zoom: bool = False
    is_pi_camera: bool = False

    @property
    def best_resolution(self) -> Optional[Resolution]:
        """Get the best (highest) resolution available."""
        if not self.resolutions:
            return RESOLUTION_1080P
        return max(self.resolutions, key=lambda r: r.pixels)


class Camera(ABC):
    """Abstract base class for cameras."""

    def __init__(self, camera_info: CameraInfo):
        self.info = camera_info
        self._running = False
        self._resolution: Resolution = RESOLUTION_1080P
        self._fps: int = 30
        self._callbacks: List[Callable[[np.ndarray], None]] = []

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def resolution(self) -> Resolution:
        return self._resolution

    @property
    def fps(self) -> int:
        return self._fps

    @abstractmethod
    async def open(self) -> bool:
        """Open the camera device."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the camera device."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start video capture."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop video capture."""
        pass

    @abstractmethod
    async def read(self) -> Optional[np.ndarray]:
        """Read a single frame."""
        pass

    @abstractmethod
    async def set_resolution(self, resolution: Resolution) -> bool:
        """Set camera resolution."""
        pass

    @abstractmethod
    async def set_fps(self, fps: int) -> bool:
        """Set frame rate."""
        pass

    def on_frame(self, callback: Callable[[np.ndarray], None]) -> None:
        """Register callback for incoming frames."""
        self._callbacks.append(callback)

    def _notify_callbacks(self, frame: np.ndarray) -> None:
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(frame)
            except Exception as e:
                logger.error(f"Frame callback error: {e}")


# Check for available backends
try:
    from picamera2 import Picamera2
    LIBCAMERA_AVAILABLE = True
except ImportError:
    LIBCAMERA_AVAILABLE = False

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class LibcameraCamera(Camera):
    """
    Camera implementation using libcamera (Picamera2).

    Recommended for Raspberry Pi Camera Module on Pi 5.
    """

    def __init__(self, camera_info: CameraInfo):
        super().__init__(camera_info)
        self._picam: Optional[Picamera2] = None
        self._config = None

    async def open(self) -> bool:
        if not LIBCAMERA_AVAILABLE:
            logger.error("libcamera (Picamera2) not available")
            return False

        try:
            camera_idx = int(self.info.id) if self.info.id.isdigit() else 0
            self._picam = Picamera2(camera_idx)

            # Create configuration
            config = self._picam.create_preview_configuration(
                main={"size": (self._resolution.width, self._resolution.height)},
                controls={"FrameRate": self._fps},
            )
            self._picam.configure(config)
            self._config = config

            logger.info(f"Opened libcamera: {self.info.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to open libcamera: {e}")
            return False

    async def close(self) -> None:
        if self._picam:
            try:
                await self.stop()
                self._picam.close()
            except Exception as e:
                logger.error(f"Error closing libcamera: {e}")
            finally:
                self._picam = None

    async def start(self) -> None:
        if self._running or not self._picam:
            return

        try:
            self._picam.start()
            self._running = True
            logger.info(f"libcamera started: {self._resolution}")
        except Exception as e:
            logger.error(f"Failed to start libcamera: {e}")
            raise

    async def stop(self) -> None:
        if not self._running or not self._picam:
            return

        try:
            self._picam.stop()
            self._running = False
            logger.info("libcamera stopped")
        except Exception as e:
            logger.error(f"Failed to stop libcamera: {e}")

    async def read(self) -> Optional[np.ndarray]:
        if not self._running or not self._picam:
            return None

        try:
            # Run in thread pool as it can block
            loop = asyncio.get_event_loop()
            frame = await loop.run_in_executor(
                None,
                self._picam.capture_array
            )

            # Convert RGBA to BGR if needed
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            elif len(frame.shape) == 3 and frame.shape[2] == 3:
                # RGB to BGR
                frame = frame[:, :, ::-1]

            self._notify_callbacks(frame)
            return frame

        except Exception as e:
            logger.error(f"Failed to read frame: {e}")
            return None

    async def set_resolution(self, resolution: Resolution) -> bool:
        try:
            self._resolution = resolution

            if self._picam:
                was_running = self._running
                if was_running:
                    await self.stop()

                config = self._picam.create_preview_configuration(
                    main={"size": (resolution.width, resolution.height)},
                    controls={"FrameRate": self._fps},
                )
                self._picam.configure(config)

                if was_running:
                    await self.start()

            return True

        except Exception as e:
            logger.error(f"Failed to set resolution: {e}")
            return False

    async def set_fps(self, fps: int) -> bool:
        try:
            self._fps = fps

            if self._picam and self._running:
                self._picam.set_controls({"FrameRate": fps})

            return True

        except Exception as e:
            logger.error(f"Failed to set FPS: {e}")
            return False


class OpenCVCamera(Camera):
    """
    Camera implementation using OpenCV.

    Works with USB webcams and as fallback for all platforms.
    """

    def __init__(self, camera_info: CameraInfo):
        super().__init__(camera_info)
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_queue: asyncio.Queue = None
        self._capture_task: Optional[asyncio.Task] = None

    async def open(self) -> bool:
        if not OPENCV_AVAILABLE:
            logger.error("OpenCV not available")
            return False

        try:
            # Determine device ID
            if self.info.device_path:
                device = self.info.device_path
            elif self.info.id.isdigit():
                device = int(self.info.id)
            else:
                device = 0

            # Open capture
            self._cap = cv2.VideoCapture(device)

            if not self._cap.isOpened():
                logger.error(f"Failed to open camera: {device}")
                return False

            # Set resolution
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution.height)
            self._cap.set(cv2.CAP_PROP_FPS, self._fps)

            # Use MJPEG for better performance with USB cameras
            self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

            self._frame_queue = asyncio.Queue(maxsize=5)

            logger.info(f"Opened OpenCV camera: {self.info.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to open OpenCV camera: {e}")
            return False

    async def close(self) -> None:
        await self.stop()

        if self._cap:
            self._cap.release()
            self._cap = None

        self._frame_queue = None

    async def start(self) -> None:
        if self._running or not self._cap:
            return

        self._running = True
        self._capture_task = asyncio.create_task(self._capture_loop())
        logger.info(f"OpenCV camera started: {self._resolution}")

    async def stop(self) -> None:
        if not self._running:
            return

        self._running = False

        if self._capture_task:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
            self._capture_task = None

        logger.info("OpenCV camera stopped")

    async def _capture_loop(self) -> None:
        """Background capture loop."""
        loop = asyncio.get_event_loop()

        while self._running:
            try:
                # Read frame in thread pool
                ret, frame = await loop.run_in_executor(
                    None,
                    self._cap.read
                )

                if not ret or frame is None:
                    await asyncio.sleep(0.01)
                    continue

                # Put in queue (drop old frames if full)
                if self._frame_queue.full():
                    try:
                        self._frame_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass

                await self._frame_queue.put(frame)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Capture error: {e}")
                await asyncio.sleep(0.1)

    async def read(self) -> Optional[np.ndarray]:
        if not self._running or not self._frame_queue:
            return None

        try:
            frame = await asyncio.wait_for(
                self._frame_queue.get(),
                timeout=1.0
            )
            self._notify_callbacks(frame)
            return frame

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Failed to read frame: {e}")
            return None

    async def set_resolution(self, resolution: Resolution) -> bool:
        try:
            self._resolution = resolution

            if self._cap:
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution.width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution.height)

            return True

        except Exception as e:
            logger.error(f"Failed to set resolution: {e}")
            return False

    async def set_fps(self, fps: int) -> bool:
        try:
            self._fps = fps

            if self._cap:
                self._cap.set(cv2.CAP_PROP_FPS, fps)

            return True

        except Exception as e:
            logger.error(f"Failed to set FPS: {e}")
            return False


def get_cameras() -> List[CameraInfo]:
    """
    Get list of available cameras.

    Returns:
        List of CameraInfo for all available cameras
    """
    cameras = []

    # Check for Pi cameras via libcamera
    if LIBCAMERA_AVAILABLE:
        try:
            from picamera2 import Picamera2
            num_cameras = Picamera2.global_camera_info()

            for idx, cam_info in enumerate(num_cameras):
                cameras.append(CameraInfo(
                    id=str(idx),
                    name=cam_info.get('Model', f'Pi Camera {idx}'),
                    backend=CameraBackend.LIBCAMERA,
                    device_path=cam_info.get('Location', ''),
                    resolutions=[
                        RESOLUTION_4K,
                        RESOLUTION_1080P,
                        RESOLUTION_720P,
                        RESOLUTION_480P,
                    ],
                    max_fps=60,
                    has_autofocus=True,
                    is_pi_camera=True,
                ))

        except Exception as e:
            logger.debug(f"libcamera enumeration failed: {e}")

    # Check for V4L2 devices
    if OPENCV_AVAILABLE:
        try:
            import os

            # Find video devices
            for device in Path("/dev").glob("video*"):
                device_num = str(device).replace("/dev/video", "")

                if not device_num.isdigit():
                    continue

                # Try to open with OpenCV
                cap = cv2.VideoCapture(int(device_num))
                if cap.isOpened():
                    # Get camera name
                    backend = cap.getBackendName()
                    name = f"USB Camera {device_num}"

                    # Try to get actual name via v4l2
                    try:
                        import subprocess
                        result = subprocess.run(
                            ["v4l2-ctl", "-d", str(device), "--info"],
                            capture_output=True,
                            text=True,
                            timeout=1,
                        )
                        for line in result.stdout.split("\n"):
                            if "Card type" in line:
                                name = line.split(":")[-1].strip()
                                break
                    except Exception:
                        pass

                    # Get supported resolutions
                    resolutions = []
                    for res in [RESOLUTION_4K, RESOLUTION_1080P, RESOLUTION_720P, RESOLUTION_480P]:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, res.width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, res.height)
                        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        if actual_w == res.width and actual_h == res.height:
                            resolutions.append(res)

                    if not resolutions:
                        resolutions = [RESOLUTION_720P]

                    # Don't add Pi cameras again
                    is_pi = "mmal" in backend.lower() or "unicam" in name.lower()
                    if not is_pi:
                        cameras.append(CameraInfo(
                            id=device_num,
                            name=name,
                            backend=CameraBackend.OPENCV,
                            device_path=str(device),
                            resolutions=resolutions,
                            max_fps=int(cap.get(cv2.CAP_PROP_FPS)) or 30,
                            has_autofocus=False,
                            is_pi_camera=False,
                        ))

                    cap.release()

        except Exception as e:
            logger.debug(f"V4L2 enumeration failed: {e}")

    return cameras


def create_camera(camera_info: CameraInfo) -> Camera:
    """
    Create a camera instance.

    Args:
        camera_info: Camera information

    Returns:
        Camera instance
    """
    if camera_info.backend == CameraBackend.LIBCAMERA and LIBCAMERA_AVAILABLE:
        return LibcameraCamera(camera_info)
    elif OPENCV_AVAILABLE:
        return OpenCVCamera(camera_info)
    else:
        raise RuntimeError("No camera backend available")
