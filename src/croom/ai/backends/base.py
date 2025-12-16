"""
Abstract base class for AI acceleration backends.

All AI backends must implement this interface to ensure
consistent behavior across different hardware.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import numpy as np


class ModelType(Enum):
    """Supported model types."""
    PERSON_DETECTION = "person_detection"
    FACE_DETECTION = "face_detection"
    POSE_ESTIMATION = "pose_estimation"
    HAND_DETECTION = "hand_detection"
    NOISE_REDUCTION = "noise_reduction"


@dataclass
class AICapabilities:
    """Capabilities of an AI backend."""
    name: str
    tops: float  # Tera Operations Per Second
    supported_models: List[ModelType]
    max_batch_size: int = 1
    supports_int8: bool = True
    supports_fp16: bool = False
    supports_fp32: bool = True


@dataclass
class DetectionResult:
    """Result of an object detection inference."""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2 normalized [0-1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox": self.bbox,
        }


@dataclass
class InferenceResult:
    """Result of an inference operation."""
    detections: List[DetectionResult]
    inference_time_ms: float
    frame_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detections": [d.to_dict() for d in self.detections],
            "inference_time_ms": self.inference_time_ms,
            "frame_id": self.frame_id,
        }


class AIBackend(ABC):
    """
    Abstract base class for AI acceleration backends.

    All backends (Hailo, Coral, NVIDIA, CPU) must implement this interface.
    """

    def __init__(self):
        self._models: Dict[str, Any] = {}
        self._initialized = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Return backend name (e.g., 'hailo', 'coral', 'nvidia', 'cpu')."""
        pass

    @abstractmethod
    def get_capabilities(self) -> AICapabilities:
        """Return backend capabilities."""
        pass

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """
        Check if this backend is available on current hardware.

        Returns:
            True if the backend can be used.
        """
        pass

    @classmethod
    def probe(cls) -> bool:
        """
        Probe for hardware without full initialization.

        Returns:
            True if hardware is detected.
        """
        return cls.is_available()

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the backend.

        Called once before first use. May load drivers, check hardware, etc.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the backend.

        Release resources, unload models, etc.
        """
        pass

    @abstractmethod
    async def load_model(self, model_type: ModelType, model_path: str) -> str:
        """
        Load a model for inference.

        Args:
            model_type: Type of model (person detection, etc.)
            model_path: Path to model file

        Returns:
            Model identifier for use in inference calls.
        """
        pass

    @abstractmethod
    async def unload_model(self, model_id: str) -> None:
        """
        Unload a model.

        Args:
            model_id: Model identifier returned from load_model.
        """
        pass

    @abstractmethod
    async def infer(
        self,
        model_id: str,
        input_data: np.ndarray,
        confidence_threshold: float = 0.5
    ) -> InferenceResult:
        """
        Run inference on input data.

        Args:
            model_id: Model identifier from load_model.
            input_data: Input image as numpy array (HWC, BGR/RGB).
            confidence_threshold: Minimum confidence for detections.

        Returns:
            InferenceResult with detections and timing.
        """
        pass

    def get_model_path(self, model_type: ModelType) -> Optional[str]:
        """
        Get the default model path for this backend and model type.

        Args:
            model_type: Type of model

        Returns:
            Path to model file, or None if not available.
        """
        # Subclasses should override with their model paths
        return None

    @property
    def is_initialized(self) -> bool:
        """Check if backend is initialized."""
        return self._initialized

    def get_loaded_models(self) -> List[str]:
        """Get list of loaded model IDs."""
        return list(self._models.keys())


class NoOpBackend(AIBackend):
    """
    No-operation backend for when AI is disabled.

    Returns empty results without doing any actual inference.
    """

    @property
    def name(self) -> str:
        return "noop"

    def get_capabilities(self) -> AICapabilities:
        return AICapabilities(
            name="noop",
            tops=0,
            supported_models=[],
            max_batch_size=0,
        )

    @classmethod
    def is_available(cls) -> bool:
        return True

    async def initialize(self) -> None:
        self._initialized = True

    async def shutdown(self) -> None:
        self._initialized = False

    async def load_model(self, model_type: ModelType, model_path: str) -> str:
        return f"noop_{model_type.value}"

    async def unload_model(self, model_id: str) -> None:
        pass

    async def infer(
        self,
        model_id: str,
        input_data: np.ndarray,
        confidence_threshold: float = 0.5
    ) -> InferenceResult:
        return InferenceResult(detections=[], inference_time_ms=0)
