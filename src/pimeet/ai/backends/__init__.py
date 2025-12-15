"""
AI acceleration backends.

Provides abstraction over different AI hardware:
- Hailo-8L (Pi AI Kit) - Raspberry Pi 5 PCIe
- Google Coral (USB/M.2) - All platforms
- NVIDIA GPU (TensorRT/CUDA) - x86_64 with NVIDIA GPU
- Intel OpenVINO - x86_64 with Intel CPU/GPU
- CPU fallback (ONNX Runtime) - All platforms
"""

from pimeet.ai.backends.base import AIBackend, AICapabilities, ModelType
from pimeet.ai.backends.onnx_cpu import ONNXCPUBackend

# Import hardware-specific backends only when available
# Priority order: Hailo > NVIDIA > Coral > Intel > CPU
_available_backends = [ONNXCPUBackend]

# Intel OpenVINO (lower priority than NVIDIA but higher than CPU)
try:
    from pimeet.ai.backends.openvino import OpenVINOBackend
    if OpenVINOBackend.is_available():
        _available_backends.insert(0, OpenVINOBackend)
except ImportError:
    pass

# Google Coral
try:
    from pimeet.ai.backends.coral import CoralBackend
    _available_backends.insert(0, CoralBackend)
except ImportError:
    pass

# NVIDIA GPU (high priority on x86_64)
try:
    from pimeet.ai.backends.nvidia import NVIDIABackend
    if NVIDIABackend.is_available():
        _available_backends.insert(0, NVIDIABackend)
except ImportError:
    pass

# Hailo (highest priority on Raspberry Pi 5)
try:
    from pimeet.ai.backends.hailo import HailoBackend
    _available_backends.insert(0, HailoBackend)
except ImportError:
    pass


def get_available_backends():
    """Return list of available backend classes in priority order."""
    return _available_backends.copy()


def get_best_backend():
    """
    Get the best available backend for the current platform.

    Returns:
        Backend class (not instance) or None if no backends available.
    """
    for backend_cls in _available_backends:
        if backend_cls.is_available():
            return backend_cls
    return None


def get_backend_by_name(name: str):
    """
    Get a backend class by name.

    Args:
        name: Backend name ('hailo', 'nvidia', 'coral', 'intel', 'cpu')

    Returns:
        Backend class or None if not found.
    """
    name_map = {
        "hailo": "HailoBackend",
        "nvidia": "NVIDIABackend",
        "coral": "CoralBackend",
        "intel": "OpenVINOBackend",
        "openvino": "OpenVINOBackend",
        "cpu": "ONNXCPUBackend",
        "onnx": "ONNXCPUBackend",
    }

    class_name = name_map.get(name.lower())
    if not class_name:
        return None

    for backend_cls in _available_backends:
        if backend_cls.__name__ == class_name:
            return backend_cls

    return None


__all__ = [
    "AIBackend",
    "AICapabilities",
    "ModelType",
    "ONNXCPUBackend",
    "get_available_backends",
    "get_best_backend",
    "get_backend_by_name",
]
