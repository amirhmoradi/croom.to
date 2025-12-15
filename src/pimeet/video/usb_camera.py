"""
USB Camera Auto-Configuration for PiMeet.

Provides automatic detection and configuration of USB webcams on x86_64 systems.
Supports a wide range of USB cameras including Logitech, Microsoft, and generic UVC cameras.
"""

import asyncio
import logging
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CameraQuality(Enum):
    """Camera quality tier based on capabilities."""
    BASIC = "basic"       # 480p, 30fps
    STANDARD = "standard" # 720p, 30fps
    HD = "hd"            # 1080p, 30fps
    PRO = "pro"          # 1080p, 60fps or 4K


class CameraFeature(Enum):
    """Camera features."""
    AUTO_FOCUS = "auto_focus"
    AUTO_EXPOSURE = "auto_exposure"
    WHITE_BALANCE = "white_balance"
    ZOOM = "zoom"
    PAN_TILT = "pan_tilt"
    FACE_TRACKING = "face_tracking"


@dataclass
class USBCameraInfo:
    """Information about a detected USB camera."""
    device_path: str
    name: str
    vendor_id: str
    product_id: str
    bus_info: str

    # Capabilities
    supported_resolutions: List[Tuple[int, int]] = field(default_factory=list)
    supported_formats: List[str] = field(default_factory=list)
    max_fps: int = 30

    # Features
    features: List[CameraFeature] = field(default_factory=list)
    quality_tier: CameraQuality = CameraQuality.STANDARD

    # Status
    is_available: bool = True
    in_use: bool = False

    def get_best_resolution(self, max_width: int = 1920) -> Tuple[int, int]:
        """Get best resolution up to max_width."""
        suitable = [r for r in self.supported_resolutions if r[0] <= max_width]
        if suitable:
            return max(suitable, key=lambda r: r[0] * r[1])
        return (1280, 720)  # Default fallback

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "device_path": self.device_path,
            "name": self.name,
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "supported_resolutions": [list(r) for r in self.supported_resolutions],
            "supported_formats": self.supported_formats,
            "max_fps": self.max_fps,
            "features": [f.value for f in self.features],
            "quality_tier": self.quality_tier.value,
            "is_available": self.is_available,
        }


# Known camera profiles for optimal configuration
CAMERA_PROFILES = {
    # Logitech cameras
    ("046d", "0825"): {"name": "Logitech C270", "quality": CameraQuality.BASIC,
                       "features": [CameraFeature.AUTO_EXPOSURE]},
    ("046d", "082d"): {"name": "Logitech HD Pro C920", "quality": CameraQuality.HD,
                       "features": [CameraFeature.AUTO_FOCUS, CameraFeature.AUTO_EXPOSURE,
                                    CameraFeature.WHITE_BALANCE, CameraFeature.ZOOM]},
    ("046d", "0893"): {"name": "Logitech StreamCam", "quality": CameraQuality.PRO,
                       "features": [CameraFeature.AUTO_FOCUS, CameraFeature.AUTO_EXPOSURE,
                                    CameraFeature.WHITE_BALANCE, CameraFeature.FACE_TRACKING]},
    ("046d", "085c"): {"name": "Logitech C930e", "quality": CameraQuality.HD,
                       "features": [CameraFeature.AUTO_FOCUS, CameraFeature.AUTO_EXPOSURE,
                                    CameraFeature.WHITE_BALANCE, CameraFeature.ZOOM,
                                    CameraFeature.PAN_TILT]},
    ("046d", "0894"): {"name": "Logitech C920 PRO HD", "quality": CameraQuality.HD,
                       "features": [CameraFeature.AUTO_FOCUS, CameraFeature.AUTO_EXPOSURE]},
    ("046d", "08e5"): {"name": "Logitech BRIO", "quality": CameraQuality.PRO,
                       "features": [CameraFeature.AUTO_FOCUS, CameraFeature.AUTO_EXPOSURE,
                                    CameraFeature.WHITE_BALANCE, CameraFeature.ZOOM,
                                    CameraFeature.FACE_TRACKING]},

    # Microsoft cameras
    ("045e", "0779"): {"name": "Microsoft LifeCam HD-3000", "quality": CameraQuality.STANDARD,
                       "features": [CameraFeature.AUTO_EXPOSURE]},
    ("045e", "0810"): {"name": "Microsoft LifeCam Cinema", "quality": CameraQuality.HD,
                       "features": [CameraFeature.AUTO_FOCUS, CameraFeature.AUTO_EXPOSURE]},
    ("045e", "0812"): {"name": "Microsoft LifeCam Studio", "quality": CameraQuality.HD,
                       "features": [CameraFeature.AUTO_FOCUS, CameraFeature.AUTO_EXPOSURE,
                                    CameraFeature.WHITE_BALANCE]},

    # Razer
    ("1532", "0e05"): {"name": "Razer Kiyo", "quality": CameraQuality.HD,
                       "features": [CameraFeature.AUTO_FOCUS, CameraFeature.AUTO_EXPOSURE]},

    # Elgato
    ("0fd9", "0066"): {"name": "Elgato Facecam", "quality": CameraQuality.PRO,
                       "features": [CameraFeature.AUTO_EXPOSURE, CameraFeature.WHITE_BALANCE]},
}


class USBCameraManager:
    """
    Manages USB camera detection and configuration.

    Provides:
    - Automatic camera detection via V4L2
    - Capability querying
    - Optimal configuration based on camera model
    - Hot-plug support
    """

    def __init__(self):
        self._cameras: Dict[str, USBCameraInfo] = {}
        self._preferred_camera: Optional[str] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False

    async def initialize(self) -> bool:
        """
        Initialize camera manager and detect cameras.

        Returns:
            True if at least one camera was found.
        """
        await self._detect_cameras()
        logger.info(f"USB Camera Manager initialized, found {len(self._cameras)} camera(s)")
        return len(self._cameras) > 0

    async def _detect_cameras(self) -> None:
        """Detect all connected USB cameras using V4L2."""
        self._cameras.clear()

        # List video devices
        video_devices = list(Path("/dev").glob("video*"))

        for device in video_devices:
            camera_info = await self._query_camera(str(device))
            if camera_info:
                self._cameras[str(device)] = camera_info

        # Set preferred camera (best quality available)
        if self._cameras:
            best_camera = max(
                self._cameras.values(),
                key=lambda c: (c.quality_tier.value, c.max_fps)
            )
            self._preferred_camera = best_camera.device_path

    async def _query_camera(self, device_path: str) -> Optional[USBCameraInfo]:
        """Query camera capabilities using v4l2-ctl."""
        try:
            # Check if it's a capture device
            proc = await asyncio.create_subprocess_exec(
                "v4l2-ctl", "-d", device_path, "--all",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)

            if proc.returncode != 0:
                return None

            output = stdout.decode()

            # Check if it's a video capture device
            if "Video Capture" not in output:
                return None

            # Parse device info
            name = self._parse_field(output, "Card type")
            bus_info = self._parse_field(output, "Bus info")

            # Skip metadata and M2M devices
            if not name or "metadata" in name.lower():
                return None

            # Extract vendor/product from bus info
            vendor_id = ""
            product_id = ""
            if bus_info:
                # Format: usb-0000:00:14.0-4
                usb_match = re.search(r'usb-([0-9a-f:\.]+)-(\d+)', bus_info)
                if usb_match:
                    # Query USB device info
                    vendor_id, product_id = await self._get_usb_ids(device_path)

            # Get supported formats and resolutions
            formats, resolutions = await self._query_formats(device_path)

            # Get features
            features = await self._query_features(device_path)

            # Determine quality tier
            quality = self._determine_quality(resolutions)

            # Check for known camera profile
            profile_key = (vendor_id.lower(), product_id.lower())
            if profile_key in CAMERA_PROFILES:
                profile = CAMERA_PROFILES[profile_key]
                name = profile.get("name", name)
                quality = profile.get("quality", quality)
                features = profile.get("features", features)

            # Get max FPS
            max_fps = 30  # Default
            if resolutions and len(resolutions) > 0:
                max_fps = await self._query_max_fps(device_path, resolutions[0])

            return USBCameraInfo(
                device_path=device_path,
                name=name,
                vendor_id=vendor_id,
                product_id=product_id,
                bus_info=bus_info,
                supported_resolutions=resolutions,
                supported_formats=formats,
                max_fps=max_fps,
                features=features,
                quality_tier=quality,
            )

        except asyncio.TimeoutError:
            logger.warning(f"Timeout querying camera {device_path}")
        except Exception as e:
            logger.debug(f"Error querying camera {device_path}: {e}")

        return None

    def _parse_field(self, output: str, field_name: str) -> str:
        """Parse a field from v4l2-ctl output."""
        for line in output.split('\n'):
            if field_name in line:
                parts = line.split(':', 1)
                if len(parts) >= 2:
                    return parts[1].strip()
        return ""

    async def _get_usb_ids(self, device_path: str) -> Tuple[str, str]:
        """Get USB vendor and product IDs for a camera."""
        try:
            # Find the device in /sys
            device_name = Path(device_path).name
            sys_path = Path(f"/sys/class/video4linux/{device_name}/device")

            if sys_path.exists():
                # Walk up to find USB device
                current = sys_path.resolve()
                for _ in range(10):  # Max depth
                    vendor_path = current / "idVendor"
                    product_path = current / "idProduct"

                    if vendor_path.exists() and product_path.exists():
                        vendor = vendor_path.read_text().strip()
                        product = product_path.read_text().strip()
                        return vendor, product

                    current = current.parent

        except Exception as e:
            logger.debug(f"Error getting USB IDs: {e}")

        return "", ""

    async def _query_formats(
        self,
        device_path: str
    ) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Query supported formats and resolutions."""
        formats = []
        resolutions = []

        try:
            proc = await asyncio.create_subprocess_exec(
                "v4l2-ctl", "-d", device_path, "--list-formats-ext",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)

            if proc.returncode == 0:
                output = stdout.decode()

                # Parse formats
                format_matches = re.findall(r"'(\w+)'", output)
                formats = list(set(format_matches))

                # Parse resolutions
                res_matches = re.findall(r'(\d+)x(\d+)', output)
                for w, h in res_matches:
                    res = (int(w), int(h))
                    if res not in resolutions:
                        resolutions.append(res)

                # Sort by size (largest first)
                resolutions.sort(key=lambda r: r[0] * r[1], reverse=True)

        except Exception as e:
            logger.debug(f"Error querying formats: {e}")

        return formats, resolutions

    async def _query_features(self, device_path: str) -> List[CameraFeature]:
        """Query camera features/controls."""
        features = []

        try:
            proc = await asyncio.create_subprocess_exec(
                "v4l2-ctl", "-d", device_path, "-L",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)

            if proc.returncode == 0:
                output = stdout.decode().lower()

                if "focus_auto" in output or "autofocus" in output:
                    features.append(CameraFeature.AUTO_FOCUS)
                if "exposure_auto" in output:
                    features.append(CameraFeature.AUTO_EXPOSURE)
                if "white_balance" in output:
                    features.append(CameraFeature.WHITE_BALANCE)
                if "zoom" in output:
                    features.append(CameraFeature.ZOOM)
                if "pan_absolute" in output or "tilt_absolute" in output:
                    features.append(CameraFeature.PAN_TILT)

        except Exception as e:
            logger.debug(f"Error querying features: {e}")

        return features

    async def _query_max_fps(
        self,
        device_path: str,
        resolution: Tuple[int, int]
    ) -> int:
        """Query maximum FPS for a resolution."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "v4l2-ctl", "-d", device_path, "--list-formats-ext",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)

            if proc.returncode == 0:
                output = stdout.decode()

                # Look for frame rate near our resolution
                pattern = rf'{resolution[0]}x{resolution[1]}.*?(\d+)\.?\d*\s*fps'
                matches = re.findall(pattern, output, re.DOTALL | re.IGNORECASE)

                if matches:
                    return max(int(m) for m in matches)

        except Exception:
            pass

        return 30  # Default

    def _determine_quality(
        self,
        resolutions: List[Tuple[int, int]]
    ) -> CameraQuality:
        """Determine quality tier based on supported resolutions."""
        if not resolutions:
            return CameraQuality.BASIC

        max_res = max(resolutions, key=lambda r: r[0] * r[1])
        max_pixels = max_res[0] * max_res[1]

        if max_pixels >= 3840 * 2160:  # 4K
            return CameraQuality.PRO
        elif max_pixels >= 1920 * 1080:  # 1080p
            return CameraQuality.HD
        elif max_pixels >= 1280 * 720:  # 720p
            return CameraQuality.STANDARD
        else:
            return CameraQuality.BASIC

    async def configure_camera(
        self,
        device_path: str,
        resolution: Optional[Tuple[int, int]] = None,
        fps: Optional[int] = None,
        auto_settings: bool = True,
    ) -> bool:
        """
        Configure camera with optimal settings.

        Args:
            device_path: Camera device path
            resolution: Target resolution (or auto-select best)
            fps: Target FPS (or use max available)
            auto_settings: Enable auto exposure/focus/WB

        Returns:
            True if configuration successful
        """
        camera = self._cameras.get(device_path)
        if not camera:
            logger.error(f"Camera not found: {device_path}")
            return False

        try:
            # Select resolution
            if not resolution:
                resolution = camera.get_best_resolution()

            # Select FPS
            if not fps:
                fps = min(camera.max_fps, 30)

            # Set format and resolution
            cmd = [
                "v4l2-ctl", "-d", device_path,
                "--set-fmt-video",
                f"width={resolution[0]},height={resolution[1]}",
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()

            # Configure auto settings
            if auto_settings:
                settings = []

                if CameraFeature.AUTO_FOCUS in camera.features:
                    settings.append("focus_auto=1")

                if CameraFeature.AUTO_EXPOSURE in camera.features:
                    settings.append("exposure_auto=3")  # Aperture priority

                if CameraFeature.WHITE_BALANCE in camera.features:
                    settings.append("white_balance_temperature_auto=1")

                for setting in settings:
                    await self._set_control(device_path, setting)

            logger.info(f"Configured camera {camera.name} at {resolution[0]}x{resolution[1]}@{fps}fps")
            return True

        except Exception as e:
            logger.error(f"Failed to configure camera: {e}")
            return False

    async def _set_control(self, device_path: str, control: str) -> bool:
        """Set a V4L2 control."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "v4l2-ctl", "-d", device_path, "-c", control,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=2.0)
            return proc.returncode == 0
        except Exception:
            return False

    async def start_monitoring(self) -> None:
        """Start monitoring for camera hot-plug events."""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Started USB camera hot-plug monitoring")

    async def stop_monitoring(self) -> None:
        """Stop monitoring for camera events."""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def _monitor_loop(self) -> None:
        """Monitor for camera changes."""
        last_devices = set(self._cameras.keys())

        while self._running:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds

                # Re-detect cameras
                await self._detect_cameras()
                current_devices = set(self._cameras.keys())

                # Check for changes
                added = current_devices - last_devices
                removed = last_devices - current_devices

                for device in added:
                    camera = self._cameras.get(device)
                    if camera:
                        logger.info(f"Camera connected: {camera.name} ({device})")

                for device in removed:
                    logger.info(f"Camera disconnected: {device}")

                last_devices = current_devices

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Camera monitor error: {e}")

    @property
    def cameras(self) -> List[USBCameraInfo]:
        """Get list of detected cameras."""
        return list(self._cameras.values())

    @property
    def preferred_camera(self) -> Optional[USBCameraInfo]:
        """Get the preferred (best) camera."""
        if self._preferred_camera:
            return self._cameras.get(self._preferred_camera)
        return None

    def get_camera(self, device_path: str) -> Optional[USBCameraInfo]:
        """Get camera by device path."""
        return self._cameras.get(device_path)

    def get_camera_by_name(self, name: str) -> Optional[USBCameraInfo]:
        """Get camera by name (partial match)."""
        name_lower = name.lower()
        for camera in self._cameras.values():
            if name_lower in camera.name.lower():
                return camera
        return None


# Singleton instance
_camera_manager: Optional[USBCameraManager] = None


def get_camera_manager() -> USBCameraManager:
    """Get USB camera manager singleton."""
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = USBCameraManager()
    return _camera_manager


async def detect_usb_cameras() -> List[USBCameraInfo]:
    """
    Convenience function to detect USB cameras.

    Returns:
        List of detected cameras.
    """
    manager = get_camera_manager()
    await manager.initialize()
    return manager.cameras
