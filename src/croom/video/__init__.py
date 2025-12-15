"""
Video module for Croom.

Provides camera capture and video processing:
- Camera abstraction (libcamera, v4l2, USB)
- Frame processing pipeline
- Resolution and format management
"""

from croom.video.service import VideoService, create_video_service
from croom.video.camera import (
    Camera,
    CameraInfo,
    CameraBackend,
    Resolution,
    get_cameras,
)
from croom.video.processor import (
    VideoProcessor,
    FrameInfo,
)

__all__ = [
    "VideoService",
    "create_video_service",
    "Camera",
    "CameraInfo",
    "CameraBackend",
    "Resolution",
    "get_cameras",
    "VideoProcessor",
    "FrameInfo",
]
