"""
Intel OpenVINO backend for AI inference.

Provides optimized inference on Intel CPUs, integrated GPUs, and discrete GPUs.
Supports Intel Core processors with UHD/Iris graphics, and Intel Arc GPUs.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

from croom.ai.backends.base import (
    AIBackend,
    AICapabilities,
    ModelType,
    InferenceResult,
    DetectionResult,
)

logger = logging.getLogger(__name__)

# OpenVINO is optional
OPENVINO_AVAILABLE = False
try:
    from openvino import Core, CompiledModel, InferRequest
    from openvino.runtime import Type as OVType
    OPENVINO_AVAILABLE = True
except ImportError:
    try:
        # Try older API
        from openvino.inference_engine import IECore
        OPENVINO_AVAILABLE = True
    except ImportError:
        pass


# COCO class names
COCO_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
}


class OpenVINOBackend(AIBackend):
    """
    Intel OpenVINO backend for AI inference.

    Supports:
    - Intel CPUs (optimized with AVX2/AVX-512)
    - Intel integrated GPUs (UHD, Iris, Xe)
    - Intel Arc discrete GPUs
    - Intel Neural Compute Stick 2 (NCS2)

    Automatically selects the best available device.
    """

    # Default model paths (OpenVINO IR format)
    MODEL_PATHS = {
        ModelType.PERSON_DETECTION: "models/yolov8n_openvino/yolov8n.xml",
        ModelType.FACE_DETECTION: "models/retinaface_openvino/retinaface.xml",
        ModelType.POSE_ESTIMATION: "models/yolov8n-pose_openvino/yolov8n-pose.xml",
    }

    # ONNX fallback paths
    ONNX_PATHS = {
        ModelType.PERSON_DETECTION: "models/yolov8n.onnx",
        ModelType.FACE_DETECTION: "models/retinaface.onnx",
    }

    def __init__(self, device: str = "AUTO"):
        """
        Initialize OpenVINO backend.

        Args:
            device: OpenVINO device string:
                - "AUTO": Automatically select best device
                - "CPU": Intel CPU
                - "GPU": Intel integrated/discrete GPU
                - "GPU.0", "GPU.1": Specific GPU device
                - "MYRIAD": Intel NCS2
                - "MULTI:GPU,CPU": Use multiple devices
        """
        super().__init__()
        self._device = device
        self._core: Optional["Core"] = None
        self._compiled_models: Dict[str, "CompiledModel"] = {}
        self._infer_requests: Dict[str, "InferRequest"] = {}
        self._model_info: Dict[str, Dict[str, Any]] = {}

        # Device info
        self._cpu_name: str = ""
        self._gpu_name: str = ""
        self._available_devices: List[str] = []
        self._selected_device: str = ""

    @property
    def name(self) -> str:
        return "intel"

    def get_capabilities(self) -> AICapabilities:
        # Estimate TOPS based on device
        tops = 2.0  # Default for CPU

        if "Arc" in self._gpu_name:
            tops = 20.0  # Intel Arc A-series
        elif "Xe" in self._gpu_name or "Iris" in self._gpu_name:
            tops = 5.0  # Iris Xe
        elif "UHD" in self._gpu_name:
            tops = 2.0  # UHD Graphics

        return AICapabilities(
            name="intel",
            tops=tops,
            supported_models=[
                ModelType.PERSON_DETECTION,
                ModelType.FACE_DETECTION,
                ModelType.POSE_ESTIMATION,
            ],
            max_batch_size=4,
            supports_int8=True,
            supports_fp16=True,
            supports_fp32=True,
        )

    @classmethod
    def is_available(cls) -> bool:
        """Check if OpenVINO is available."""
        return OPENVINO_AVAILABLE

    @classmethod
    def probe(cls) -> bool:
        """Probe for Intel hardware without full initialization."""
        if not OPENVINO_AVAILABLE:
            return False

        try:
            core = Core()
            devices = core.available_devices
            # Check for any Intel device
            return len(devices) > 0
        except Exception:
            return False

    async def initialize(self) -> None:
        """Initialize OpenVINO backend."""
        if not OPENVINO_AVAILABLE:
            raise RuntimeError("OpenVINO not installed")

        try:
            self._core = Core()

            # Get available devices
            self._available_devices = self._core.available_devices
            logger.info(f"OpenVINO available devices: {self._available_devices}")

            # Detect device info
            await self._detect_devices()

            # Select device
            if self._device == "AUTO":
                self._selected_device = self._select_best_device()
            else:
                self._selected_device = self._device

            logger.info(f"OpenVINO initialized with device: {self._selected_device}")
            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize OpenVINO: {e}")
            raise

    async def _detect_devices(self) -> None:
        """Detect CPU and GPU info."""
        try:
            # CPU info
            if "CPU" in self._available_devices:
                self._cpu_name = self._core.get_property("CPU", "FULL_DEVICE_NAME")
                logger.debug(f"CPU: {self._cpu_name}")

            # GPU info
            for device in self._available_devices:
                if device.startswith("GPU"):
                    self._gpu_name = self._core.get_property(device, "FULL_DEVICE_NAME")
                    logger.debug(f"GPU ({device}): {self._gpu_name}")
                    break

        except Exception as e:
            logger.warning(f"Could not detect device info: {e}")

    def _select_best_device(self) -> str:
        """Select the best available device."""
        # Priority: Arc GPU > Xe/Iris GPU > UHD GPU > CPU

        for device in self._available_devices:
            if device.startswith("GPU"):
                try:
                    gpu_name = self._core.get_property(device, "FULL_DEVICE_NAME")
                    if "Arc" in gpu_name:
                        return device
                except Exception:
                    pass

        for device in self._available_devices:
            if device.startswith("GPU"):
                try:
                    gpu_name = self._core.get_property(device, "FULL_DEVICE_NAME")
                    if "Xe" in gpu_name or "Iris" in gpu_name:
                        return device
                except Exception:
                    pass

        # Any GPU is better than CPU for inference
        for device in self._available_devices:
            if device.startswith("GPU"):
                return device

        # Fall back to CPU
        if "CPU" in self._available_devices:
            return "CPU"

        return "AUTO"

    async def shutdown(self) -> None:
        """Shutdown and release resources."""
        for model_id in list(self._compiled_models.keys()):
            await self.unload_model(model_id)

        self._core = None
        self._initialized = False
        logger.info("OpenVINO backend shutdown")

    def get_model_path(self, model_type: ModelType) -> Optional[str]:
        """Get default model path for model type."""
        # Prefer OpenVINO IR format
        ir_path = self.MODEL_PATHS.get(model_type)
        if ir_path and Path(ir_path).exists():
            return ir_path

        # Fall back to ONNX
        return self.ONNX_PATHS.get(model_type)

    async def load_model(self, model_type: ModelType, model_path: str) -> str:
        """
        Load a model for inference.

        Args:
            model_type: Type of model
            model_path: Path to model file (.xml or .onnx)

        Returns:
            Model identifier
        """
        if not self._initialized:
            raise RuntimeError("Backend not initialized")

        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        model_id = f"{model_type.value}_{path.stem}"

        try:
            # Read model
            model = self._core.read_model(str(path))

            # Configure model for optimal performance
            config = {}

            if self._selected_device == "CPU":
                # CPU optimizations
                config["PERFORMANCE_HINT"] = "LATENCY"
                config["NUM_STREAMS"] = "1"
                config["INFERENCE_PRECISION_HINT"] = "f32"
            elif self._selected_device.startswith("GPU"):
                # GPU optimizations
                config["PERFORMANCE_HINT"] = "LATENCY"
                config["CACHE_DIR"] = "/tmp/openvino_cache"

            # Compile model
            compiled_model = self._core.compile_model(
                model,
                self._selected_device,
                config
            )

            # Create inference request
            infer_request = compiled_model.create_infer_request()

            self._compiled_models[model_id] = compiled_model
            self._infer_requests[model_id] = infer_request

            # Get input/output info
            input_layer = compiled_model.input(0)
            output_layers = list(compiled_model.outputs)

            self._model_info[model_id] = {
                "type": model_type,
                "path": str(path),
                "input_name": input_layer.any_name,
                "input_shape": list(input_layer.shape),
                "output_names": [o.any_name for o in output_layers],
            }

            logger.info(f"Loaded OpenVINO model: {model_id} on {self._selected_device}")
            return model_id

        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            raise

    async def unload_model(self, model_id: str) -> None:
        """Unload a model."""
        if model_id in self._infer_requests:
            del self._infer_requests[model_id]

        if model_id in self._compiled_models:
            del self._compiled_models[model_id]

        if model_id in self._model_info:
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
        if model_id not in self._infer_requests:
            raise ValueError(f"Model not loaded: {model_id}")

        infer_request = self._infer_requests[model_id]
        info = self._model_info[model_id]

        start_time = time.perf_counter()

        # Preprocess
        input_tensor = self._preprocess(input_data, info["input_shape"])

        # Run inference
        infer_request.infer({info["input_name"]: input_tensor})

        # Get outputs
        outputs = []
        for output_name in info["output_names"]:
            output_tensor = infer_request.get_tensor(output_name)
            outputs.append(output_tensor.data.copy())

        # Postprocess
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
        """Preprocess image for model input."""
        import cv2

        # Determine target size
        if len(input_shape) == 4:
            if input_shape[1] == 3:  # NCHW
                target_h, target_w = input_shape[2], input_shape[3]
            else:  # NHWC
                target_h, target_w = input_shape[1], input_shape[2]
        else:
            target_h, target_w = 640, 640

        # Handle dynamic shapes
        if target_h <= 0:
            target_h = 640
        if target_w <= 0:
            target_w = 640

        # Resize
        resized = cv2.resize(image, (target_w, target_h))

        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Normalize to [0, 1]
        normalized = rgb.astype(np.float32) / 255.0

        # Transpose to NCHW
        if len(input_shape) == 4 and input_shape[1] == 3:
            tensor = np.transpose(normalized, (2, 0, 1))
        else:
            tensor = normalized

        # Add batch dimension
        tensor = np.expand_dims(tensor, axis=0)

        return np.ascontiguousarray(tensor)

    def _postprocess(
        self,
        outputs: List[np.ndarray],
        model_type: ModelType,
        original_size: Tuple[int, int],
        confidence_threshold: float
    ) -> List[DetectionResult]:
        """Postprocess model outputs."""
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
        output = outputs[0]

        if output.ndim == 3:
            output = output[0]

        # Handle YOLOv8 format
        if output.shape[-1] == 84 or output.shape[0] == 84:
            if output.shape[0] == 84:
                output = output.T

            for det in output:
                x_center, y_center, w, h = det[:4]
                class_scores = det[4:]
                class_id = np.argmax(class_scores)
                confidence = class_scores[class_id]

                if confidence < confidence_threshold:
                    continue

                if class_id != 0:  # Only person
                    continue

                x1 = (x_center - w / 2) / 640
                y1 = (y_center - h / 2) / 640
                x2 = (x_center + w / 2) / 640
                y2 = (y_center + h / 2) / 640

                detections.append(DetectionResult(
                    class_id=int(class_id),
                    class_name=COCO_CLASSES.get(int(class_id), "unknown"),
                    confidence=float(confidence),
                    bbox=(float(x1), float(y1), float(x2), float(y2))
                ))

        return self._nms(detections)

    def _postprocess_faces(
        self,
        outputs: List[np.ndarray],
        original_size: Tuple[int, int],
        confidence_threshold: float
    ) -> List[DetectionResult]:
        """Postprocess face detection output."""
        return []

    def _nms(
        self,
        detections: List[DetectionResult],
        iou_threshold: float = 0.45
    ) -> List[DetectionResult]:
        """Apply Non-Maximum Suppression."""
        if not detections:
            return []

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

    @property
    def device(self) -> str:
        """Get the selected device."""
        return self._selected_device

    @property
    def available_devices(self) -> List[str]:
        """Get list of available devices."""
        return self._available_devices.copy()

    @property
    def cpu_name(self) -> str:
        """Get CPU name."""
        return self._cpu_name

    @property
    def gpu_name(self) -> str:
        """Get GPU name."""
        return self._gpu_name
