"""
Platform detection and hardware abstraction layer.

This module provides platform-agnostic interfaces for hardware features,
enabling the same codebase to run on Raspberry Pi, x86_64 PCs, NUCs, and more.
"""

from pimeet.platform.detector import (
    PlatformDetector,
    PlatformInfo,
    DeviceType,
    Architecture,
    GPUVendor,
    GPUInfo,
    get_platform_info,
)
from pimeet.platform.capabilities import Capabilities
from pimeet.platform.hal import (
    GPIOMode,
    GPIOPull,
    GPIOEdge,
    GPIOPin,
    GPIOInterface,
    I2CInterface,
    CameraInterface,
    DisplayInterface,
    HardwareAbstractionLayer,
    StubGPIO,
    get_hal,
)
from pimeet.platform.profiles import (
    HardwareProfile,
    PerformanceTier,
    ProfileManager,
    detect_profile,
    get_profile_for_device,
    get_profile_manager,
)

__all__ = [
    # Platform detection
    "PlatformDetector",
    "PlatformInfo",
    "DeviceType",
    "Architecture",
    "GPUVendor",
    "GPUInfo",
    "get_platform_info",
    # Capabilities
    "Capabilities",
    # HAL
    "GPIOMode",
    "GPIOPull",
    "GPIOEdge",
    "GPIOPin",
    "GPIOInterface",
    "I2CInterface",
    "CameraInterface",
    "DisplayInterface",
    "HardwareAbstractionLayer",
    "StubGPIO",
    "get_hal",
    # Hardware profiles
    "HardwareProfile",
    "PerformanceTier",
    "ProfileManager",
    "detect_profile",
    "get_profile_for_device",
    "get_profile_manager",
]
