"""
Platform detection and hardware abstraction layer.

This module provides platform-agnostic interfaces for hardware features,
enabling the same codebase to run on Raspberry Pi and PC platforms.
"""

from pimeet.platform.detector import PlatformDetector, PlatformInfo
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
    get_hal,
)

__all__ = [
    "PlatformDetector",
    "PlatformInfo",
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
    "get_hal",
]
