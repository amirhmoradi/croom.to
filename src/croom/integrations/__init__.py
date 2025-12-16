"""
Integrations module for Croom.

Provides integrations with external services:
- Vexa (meeting transcription and intelligence)
"""

from croom.integrations.vexa import (
    VexaClient,
    VexaConfig,
    VexaService,
    TranscriptionSession,
    TranscriptionSegment,
    TranscriptionLanguage,
    TranscriptionStatus,
    MeetingSummary,
    ActionItem,
    create_vexa_service,
)

__all__ = [
    "VexaClient",
    "VexaConfig",
    "VexaService",
    "TranscriptionSession",
    "TranscriptionSegment",
    "TranscriptionLanguage",
    "TranscriptionStatus",
    "MeetingSummary",
    "ActionItem",
    "create_vexa_service",
]
