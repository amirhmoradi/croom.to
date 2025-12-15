"""
AI features for PiMeet.

This module provides AI-powered features including:
- Person detection
- Face detection
- Auto-framing
- Noise reduction
- Occupancy counting
"""

from pimeet.ai.service import AIService
from pimeet.ai.backends.base import AIBackend

__all__ = [
    "AIService",
    "AIBackend",
]
