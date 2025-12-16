"""
AI Service for Croom.

High-level service that manages AI backends and provides
unified access to AI features.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
import numpy as np

from croom.core.config import Config
from croom.core.service import Service, ServiceState
from croom.platform.capabilities import Capabilities
from croom.ai.backends.base import (
    AIBackend,
    ModelType,
    InferenceResult,
    NoOpBackend,
)
from croom.ai.backends import get_available_backends

logger = logging.getLogger(__name__)


class AIService(Service):
    """
    High-level AI service that manages backends and provides AI features.

    Automatically selects the best available backend and handles
    model loading/unloading.
    """

    def __init__(self, config: Config, capabilities: Capabilities):
        super().__init__("ai")
        self.config = config
        self.capabilities = capabilities

        self._backend: Optional[AIBackend] = None
        self._loaded_models: Dict[ModelType, str] = {}

        # Feature flags from config
        self._person_detection_enabled = config.ai.person_detection
        self._face_detection_enabled = config.ai.auto_framing  # Face detection for framing
        self._occupancy_enabled = config.ai.occupancy_counting

    async def start(self) -> None:
        """Start AI service."""
        if self.config.ai.privacy_mode:
            logger.info("Privacy mode enabled, using NoOp backend")
            self._backend = NoOpBackend()
            await self._backend.initialize()
            return

        # Select and initialize backend
        self._backend = self._select_backend()
        await self._backend.initialize()

        # Load required models
        await self._load_models()

        logger.info(f"AI service started with {self._backend.name} backend")

    async def stop(self) -> None:
        """Stop AI service."""
        # Unload models
        for model_type, model_id in list(self._loaded_models.items()):
            try:
                await self._backend.unload_model(model_id)
            except Exception as e:
                logger.error(f"Error unloading model {model_id}: {e}")

        self._loaded_models.clear()

        # Shutdown backend
        if self._backend:
            await self._backend.shutdown()
            self._backend = None

        logger.info("AI service stopped")

    def _select_backend(self) -> AIBackend:
        """
        Select the best available AI backend.

        Returns:
            Selected backend instance.
        """
        config_backend = self.config.ai.backend

        available = get_available_backends()

        if not available:
            logger.warning("No AI backends available, using NoOp")
            return NoOpBackend()

        # Check for specific backend request
        if config_backend != "auto":
            for backend_cls in available:
                backend = backend_cls()
                if backend.name == config_backend and backend_cls.is_available():
                    logger.info(f"Using configured backend: {config_backend}")
                    return backend

            logger.warning(f"Configured backend '{config_backend}' not available")

        # Auto-select based on capabilities
        priority_order = ["hailo", "nvidia", "coral", "cpu"]

        for name in priority_order:
            for backend_cls in available:
                backend = backend_cls()
                if backend.name == name and backend_cls.is_available():
                    logger.info(f"Auto-selected backend: {name}")
                    return backend

        # Fallback to first available
        backend = available[0]()
        logger.info(f"Fallback to backend: {backend.name}")
        return backend

    async def _load_models(self) -> None:
        """Load configured AI models."""
        if self._person_detection_enabled or self._occupancy_enabled:
            await self._load_model(ModelType.PERSON_DETECTION)

        if self._face_detection_enabled:
            await self._load_model(ModelType.FACE_DETECTION)

    async def _load_model(self, model_type: ModelType) -> Optional[str]:
        """Load a specific model type."""
        if model_type in self._loaded_models:
            return self._loaded_models[model_type]

        model_path = self._backend.get_model_path(model_type)
        if not model_path:
            logger.warning(f"No model path for {model_type.value}")
            return None

        try:
            model_id = await self._backend.load_model(model_type, model_path)
            self._loaded_models[model_type] = model_id
            return model_id
        except Exception as e:
            logger.error(f"Failed to load {model_type.value}: {e}")
            return None

    async def detect_persons(
        self,
        frame: np.ndarray,
        confidence_threshold: float = 0.5
    ) -> InferenceResult:
        """
        Detect persons in a video frame.

        Args:
            frame: Input frame (HWC, BGR, uint8)
            confidence_threshold: Minimum detection confidence

        Returns:
            InferenceResult with person detections
        """
        if not self._person_detection_enabled:
            return InferenceResult(detections=[], inference_time_ms=0)

        model_id = self._loaded_models.get(ModelType.PERSON_DETECTION)
        if not model_id:
            return InferenceResult(detections=[], inference_time_ms=0)

        return await self._backend.infer(model_id, frame, confidence_threshold)

    async def detect_faces(
        self,
        frame: np.ndarray,
        confidence_threshold: float = 0.5
    ) -> InferenceResult:
        """
        Detect faces in a video frame.

        Args:
            frame: Input frame (HWC, BGR, uint8)
            confidence_threshold: Minimum detection confidence

        Returns:
            InferenceResult with face detections
        """
        if not self._face_detection_enabled:
            return InferenceResult(detections=[], inference_time_ms=0)

        model_id = self._loaded_models.get(ModelType.FACE_DETECTION)
        if not model_id:
            return InferenceResult(detections=[], inference_time_ms=0)

        return await self._backend.infer(model_id, frame, confidence_threshold)

    def get_occupancy_count(self, result: InferenceResult) -> int:
        """
        Get occupancy count from person detection result.

        Args:
            result: Person detection result

        Returns:
            Number of persons detected
        """
        return len(result.detections)

    def calculate_auto_frame_roi(
        self,
        detections: InferenceResult,
        frame_size: tuple,
        padding: float = 0.1
    ) -> Optional[tuple]:
        """
        Calculate region of interest for auto-framing.

        Args:
            detections: Person or face detections
            frame_size: (width, height) of frame
            padding: Padding ratio around detected persons

        Returns:
            (x1, y1, x2, y2) normalized ROI, or None if no detections
        """
        if not detections.detections:
            return None

        # Get bounding box that contains all detections
        min_x = min(d.bbox[0] for d in detections.detections)
        min_y = min(d.bbox[1] for d in detections.detections)
        max_x = max(d.bbox[2] for d in detections.detections)
        max_y = max(d.bbox[3] for d in detections.detections)

        # Add padding
        width = max_x - min_x
        height = max_y - min_y

        min_x = max(0, min_x - width * padding)
        min_y = max(0, min_y - height * padding)
        max_x = min(1, max_x + width * padding)
        max_y = min(1, max_y + height * padding)

        return (min_x, min_y, max_x, max_y)

    @property
    def backend_name(self) -> str:
        """Get name of active backend."""
        return self._backend.name if self._backend else "none"

    @property
    def backend_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of active backend."""
        if not self._backend:
            return {}
        caps = self._backend.get_capabilities()
        return {
            "name": caps.name,
            "tops": caps.tops,
            "supported_models": [m.value for m in caps.supported_models],
        }

    def get_status(self) -> Dict[str, Any]:
        """Get AI service status."""
        return {
            "running": self.is_running,
            "backend": self.backend_name,
            "capabilities": self.backend_capabilities,
            "loaded_models": list(self._loaded_models.keys()),
            "features": {
                "person_detection": self._person_detection_enabled,
                "face_detection": self._face_detection_enabled,
                "occupancy_counting": self._occupancy_enabled,
            }
        }
