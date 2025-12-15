"""
ONNX Runtime CPU backend.

Provides CPU-based inference using ONNX Runtime.
This is the fallback backend available on all platforms.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

from pimeet.ai.backends.base import (
    AIBackend,
    AICapabilities,
    ModelType,
    InferenceResult,
    DetectionResult,
)

logger = logging.getLogger(__name__)

# ONNX Runtime is optional
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    ort = None


# COCO class names for person detection
COCO_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    # ... abbreviated for space, full list in production
}


class ONNXCPUBackend(AIBackend):
    """
    ONNX Runtime CPU backend for inference.

    Uses ONNX Runtime with CPU execution provider.
    Works on all platforms but slower than accelerated backends.
    """

    # Default model paths
    MODEL_PATHS = {
        ModelType.PERSON_DETECTION: "models/yolov8n.onnx",
        ModelType.FACE_DETECTION: "models/retinaface.onnx",
    }

    def __init__(self):
        super().__init__()
        self._sessions: Dict[str, "ort.InferenceSession"] = {}
        self._model_info: Dict[str, Dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return "cpu"

    def get_capabilities(self) -> AICapabilities:
        return AICapabilities(
            name="cpu",
            tops=0.1,  # Very rough estimate for CPU
            supported_models=[
                ModelType.PERSON_DETECTION,
                ModelType.FACE_DETECTION,
            ],
            max_batch_size=1,
            supports_int8=False,
            supports_fp16=False,
            supports_fp32=True,
        )

    @classmethod
    def is_available(cls) -> bool:
        """CPU backend is always available if ONNX Runtime is installed."""
        return ONNX_AVAILABLE

    async def initialize(self) -> None:
        """Initialize ONNX Runtime."""
        if not ONNX_AVAILABLE:
            raise RuntimeError("ONNX Runtime not installed")

        # Configure session options for efficiency
        self._session_options = ort.SessionOptions()
        self._session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session_options.intra_op_num_threads = 4
        self._session_options.inter_op_num_threads = 1

        self._initialized = True
        logger.info("ONNX CPU backend initialized")

    async def shutdown(self) -> None:
        """Shutdown and release resources."""
        for model_id in list(self._sessions.keys()):
            await self.unload_model(model_id)

        self._initialized = False
        logger.info("ONNX CPU backend shutdown")

    def get_model_path(self, model_type: ModelType) -> Optional[str]:
        """Get default model path for model type."""
        return self.MODEL_PATHS.get(model_type)

    async def load_model(self, model_type: ModelType, model_path: str) -> str:
        """
        Load an ONNX model.

        Args:
            model_type: Type of model
            model_path: Path to .onnx file

        Returns:
            Model identifier
        """
        if not self._initialized:
            raise RuntimeError("Backend not initialized")

        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        model_id = f"{model_type.value}_{Path(model_path).stem}"

        try:
            session = ort.InferenceSession(
                model_path,
                self._session_options,
                providers=["CPUExecutionProvider"]
            )

            # Get model input/output info
            input_info = session.get_inputs()[0]
            output_info = session.get_outputs()

            self._sessions[model_id] = session
            self._model_info[model_id] = {
                "type": model_type,
                "path": model_path,
                "input_name": input_info.name,
                "input_shape": input_info.shape,
                "output_names": [o.name for o in output_info],
            }

            logger.info(f"Loaded model: {model_id} (input: {input_info.shape})")
            return model_id

        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            raise

    async def unload_model(self, model_id: str) -> None:
        """Unload a model."""
        if model_id in self._sessions:
            del self._sessions[model_id]
            del self._model_info[model_id]
            logger.info(f"Unloaded model: {model_id}")

    async def infer(
        self,
        model_id: str,
        input_data: np.ndarray,
        confidence_threshold: float = 0.5
    ) -> InferenceResult:
        """
        Run inference on input image.

        Args:
            model_id: Model identifier
            input_data: Input image (HWC, uint8, BGR)
            confidence_threshold: Minimum detection confidence

        Returns:
            InferenceResult with detections
        """
        if model_id not in self._sessions:
            raise ValueError(f"Model not loaded: {model_id}")

        session = self._sessions[model_id]
        info = self._model_info[model_id]

        start_time = time.perf_counter()

        # Preprocess input
        input_tensor = self._preprocess(input_data, info["input_shape"])

        # Run inference
        outputs = session.run(
            info["output_names"],
            {info["input_name"]: input_tensor}
        )

        # Postprocess based on model type
        detections = self._postprocess(
            outputs,
            info["type"],
            input_data.shape[:2],
            confidence_threshold
        )

        inference_time = (time.perf_counter() - start_time) * 1000

        return InferenceResult(
            detections=detections,
            inference_time_ms=inference_time
        )

    def _preprocess(
        self,
        image: np.ndarray,
        input_shape: List[int]
    ) -> np.ndarray:
        """
        Preprocess image for model input.

        Args:
            image: Input image (HWC, uint8)
            input_shape: Model input shape [N, C, H, W] or [N, H, W, C]

        Returns:
            Preprocessed tensor
        """
        import cv2

        # Determine target size
        if len(input_shape) == 4:
            if input_shape[1] == 3:  # NCHW
                target_h, target_w = input_shape[2], input_shape[3]
            else:  # NHWC
                target_h, target_w = input_shape[1], input_shape[2]
        else:
            target_h, target_w = 640, 640  # Default

        # Resize
        resized = cv2.resize(image, (target_w, target_h))

        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Normalize to [0, 1]
        normalized = rgb.astype(np.float32) / 255.0

        # Transpose to NCHW if needed
        if len(input_shape) == 4 and input_shape[1] == 3:
            tensor = np.transpose(normalized, (2, 0, 1))
        else:
            tensor = normalized

        # Add batch dimension
        tensor = np.expand_dims(tensor, axis=0)

        return tensor

    def _postprocess(
        self,
        outputs: List[np.ndarray],
        model_type: ModelType,
        original_size: Tuple[int, int],
        confidence_threshold: float
    ) -> List[DetectionResult]:
        """
        Postprocess model outputs to detections.

        Args:
            outputs: Model output tensors
            model_type: Type of model
            original_size: Original image (H, W)
            confidence_threshold: Minimum confidence

        Returns:
            List of detections
        """
        if model_type == ModelType.PERSON_DETECTION:
            return self._postprocess_yolo(outputs, original_size, confidence_threshold)
        elif model_type == ModelType.FACE_DETECTION:
            return self._postprocess_faces(outputs, original_size, confidence_threshold)
        else:
            return []

    def _postprocess_yolo(
        self,
        outputs: List[np.ndarray],
        original_size: Tuple[int, int],
        confidence_threshold: float
    ) -> List[DetectionResult]:
        """Postprocess YOLO detection output."""
        detections = []

        # YOLOv8 output format: [batch, num_detections, 4+num_classes]
        # or transposed depending on export
        output = outputs[0]

        if output.ndim == 3:
            output = output[0]  # Remove batch dim

        # Handle YOLOv8 format (84 = 4 bbox + 80 classes)
        if output.shape[-1] == 84 or output.shape[0] == 84:
            if output.shape[0] == 84:
                output = output.T  # Transpose to [num_detections, 84]

            for det in output:
                x_center, y_center, w, h = det[:4]
                class_scores = det[4:]
                class_id = np.argmax(class_scores)
                confidence = class_scores[class_id]

                if confidence < confidence_threshold:
                    continue

                # Only keep person detections (class 0)
                if class_id != 0:
                    continue

                # Convert to normalized x1, y1, x2, y2
                x1 = (x_center - w / 2) / 640  # Assuming 640x640 input
                y1 = (y_center - h / 2) / 640
                x2 = (x_center + w / 2) / 640
                y2 = (y_center + h / 2) / 640

                detections.append(DetectionResult(
                    class_id=int(class_id),
                    class_name=COCO_CLASSES.get(int(class_id), "unknown"),
                    confidence=float(confidence),
                    bbox=(float(x1), float(y1), float(x2), float(y2))
                ))

        # Apply NMS
        detections = self._nms(detections, iou_threshold=0.45)

        return detections

    def _postprocess_faces(
        self,
        outputs: List[np.ndarray],
        original_size: Tuple[int, int],
        confidence_threshold: float
    ) -> List[DetectionResult]:
        """Postprocess face detection output."""
        # Simplified face detection postprocessing
        detections = []

        # Implementation depends on specific face model format
        # This is a placeholder for RetinaFace or similar

        return detections

    def _nms(
        self,
        detections: List[DetectionResult],
        iou_threshold: float = 0.45
    ) -> List[DetectionResult]:
        """
        Apply Non-Maximum Suppression.

        Args:
            detections: List of detections
            iou_threshold: IoU threshold for suppression

        Returns:
            Filtered detections
        """
        if not detections:
            return []

        # Sort by confidence
        detections = sorted(detections, key=lambda x: x.confidence, reverse=True)

        keep = []
        while detections:
            best = detections.pop(0)
            keep.append(best)

            detections = [
                d for d in detections
                if self._iou(best.bbox, d.bbox) < iou_threshold
            ]

        return keep

    def _iou(
        self,
        box1: Tuple[float, float, float, float],
        box2: Tuple[float, float, float, float]
    ) -> float:
        """Calculate Intersection over Union."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)

        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0
