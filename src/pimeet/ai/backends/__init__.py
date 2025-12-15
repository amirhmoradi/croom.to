"""
AI acceleration backends.

Provides abstraction over different AI hardware:
- Hailo-8L (Pi AI Kit)
- Google Coral (USB/M.2)
- NVIDIA GPU (future)
- CPU fallback (ONNX Runtime)
"""

from pimeet.ai.backends.base import AIBackend, AICapabilities
from pimeet.ai.backends.onnx_cpu import ONNXCPUBackend

# Import hardware-specific backends only when available
_available_backends = [ONNXCPUBackend]

try:
    from pimeet.ai.backends.hailo import HailoBackend
    _available_backends.insert(0, HailoBackend)
except ImportError:
    pass

try:
    from pimeet.ai.backends.coral import CoralBackend
    _available_backends.insert(0, CoralBackend)
except ImportError:
    pass


def get_available_backends():
    """Return list of available backend classes."""
    return _available_backends


__all__ = [
    "AIBackend",
    "AICapabilities",
    "ONNXCPUBackend",
    "get_available_backends",
]
