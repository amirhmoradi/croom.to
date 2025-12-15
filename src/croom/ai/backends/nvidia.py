"""
NVIDIA TensorRT backend for GPU-accelerated AI inference.

Provides high-performance inference on NVIDIA GPUs using TensorRT.
Supports CUDA for general GPU acceleration and TensorRT for optimized models.
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

# TensorRT and CUDA are optional
TENSORRT_AVAILABLE = False
CUDA_AVAILABLE = False

try:
    import tensorrt as trt
    TENSORRT_AVAILABLE = True
except ImportError:
    trt = None

try:
    import pycuda.driver as cuda
    import pycuda.autoinit
    CUDA_AVAILABLE = True
except ImportError:
    cuda = None

# Also support ONNX Runtime with CUDA
ONNX_CUDA_AVAILABLE = False
try:
    import onnxruntime as ort
    providers = ort.get_available_providers()
    ONNX_CUDA_AVAILABLE = "CUDAExecutionProvider" in providers
except ImportError:
    ort = None


# COCO class names
COCO_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
}


class NVIDIABackend(AIBackend):
    """
    NVIDIA GPU backend for AI inference.

    Supports three modes:
    1. TensorRT (highest performance) - requires .engine files
    2. ONNX Runtime with CUDA - uses .onnx files with GPU acceleration
    3. Pure CUDA - for custom operations

    Automatically selects the best available mode.
    """

    # Default model paths
    MODEL_PATHS = {
        ModelType.PERSON_DETECTION: "models/yolov8n.engine",
        ModelType.FACE_DETECTION: "models/retinaface.engine",
        ModelType.POSE_ESTIMATION: "models/yolov8n-pose.engine",
        ModelType.HAND_DETECTION: "models/hand_detection.engine",
    }

    # ONNX fallback paths
    ONNX_PATHS = {
        ModelType.PERSON_DETECTION: "models/yolov8n.onnx",
        ModelType.FACE_DETECTION: "models/retinaface.onnx",
    }

    def __init__(self):
        super().__init__()
        self._mode: Optional[str] = None  # 'tensorrt', 'onnx_cuda', or None
        self._gpu_name: str = "Unknown NVIDIA GPU"
        self._gpu_memory_mb: int = 0

        # TensorRT resources
        self._trt_logger = None
        self._trt_runtime = None
        self._trt_engines: Dict[str, Any] = {}
        self._trt_contexts: Dict[str, Any] = {}

        # ONNX Runtime resources
        self._ort_sessions: Dict[str, Any] = {}
        self._ort_session_options = None

        # Model metadata
        self._model_info: Dict[str, Dict[str, Any]] = {}

        # CUDA stream
        self._cuda_stream = None

    @property
    def name(self) -> str:
        return "nvidia"

    def get_capabilities(self) -> AICapabilities:
        # Estimate TOPS based on GPU
        tops = 20.0  # Default for mid-range GPU

        if "4090" in self._gpu_name or "4080" in self._gpu_name:
            tops = 80.0
        elif "3090" in self._gpu_name or "3080" in self._gpu_name:
            tops = 40.0
        elif "3070" in self._gpu_name or "3060" in self._gpu_name:
            tops = 20.0
        elif "2080" in self._gpu_name or "2070" in self._gpu_name:
            tops = 15.0

        return AICapabilities(
            name="nvidia",
            tops=tops,
            supported_models=[
                ModelType.PERSON_DETECTION,
                ModelType.FACE_DETECTION,
                ModelType.POSE_ESTIMATION,
                ModelType.HAND_DETECTION,
            ],
            max_batch_size=8,
            supports_int8=True,
            supports_fp16=True,
            supports_fp32=True,
        )

    @classmethod
    def is_available(cls) -> bool:
        """Check if NVIDIA GPU acceleration is available."""
        if TENSORRT_AVAILABLE and CUDA_AVAILABLE:
            return True
        if ONNX_CUDA_AVAILABLE:
            return True
        return False

    @classmethod
    def probe(cls) -> bool:
        """Probe for NVIDIA GPU without full initialization."""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            return False

    async def initialize(self) -> None:
        """Initialize NVIDIA backend."""
        # Detect GPU info
        await self._detect_gpu()

        # Initialize TensorRT if available
        if TENSORRT_AVAILABLE and CUDA_AVAILABLE:
            try:
                self._trt_logger = trt.Logger(trt.Logger.WARNING)
                self._trt_runtime = trt.Runtime(self._trt_logger)
                self._mode = "tensorrt"
                logger.info(f"TensorRT backend initialized on {self._gpu_name}")
            except Exception as e:
                logger.warning(f"TensorRT init failed: {e}, falling back to ONNX")
                self._mode = None

        # Fall back to ONNX Runtime with CUDA
        if not self._mode and ONNX_CUDA_AVAILABLE:
            try:
                self._ort_session_options = ort.SessionOptions()
                self._ort_session_options.graph_optimization_level = (
                    ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                )
                self._mode = "onnx_cuda"
                logger.info(f"ONNX-CUDA backend initialized on {self._gpu_name}")
            except Exception as e:
                logger.error(f"ONNX-CUDA init failed: {e}")
                raise RuntimeError("No NVIDIA acceleration available")

        if not self._mode:
            raise RuntimeError("No NVIDIA acceleration available")

        self._initialized = True

    async def _detect_gpu(self) -> None:
        """Detect GPU name and memory."""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                if len(parts) >= 2:
                    self._gpu_name = parts[0].strip()
                    self._gpu_memory_mb = int(float(parts[1].strip()))
        except Exception as e:
            logger.warning(f"Could not detect GPU info: {e}")

    async def shutdown(self) -> None:
        """Shutdown and release resources."""
        # Unload all models
        for model_id in list(self._trt_engines.keys()):
            await self.unload_model(model_id)

        for model_id in list(self._ort_sessions.keys()):
            await self.unload_model(model_id)

        self._trt_logger = None
        self._trt_runtime = None
        self._initialized = False

        logger.info("NVIDIA backend shutdown")

    def get_model_path(self, model_type: ModelType) -> Optional[str]:
        """Get default model path for model type."""
        if self._mode == "tensorrt":
            return self.MODEL_PATHS.get(model_type)
        else:
            return self.ONNX_PATHS.get(model_type)

    async def load_model(self, model_type: ModelType, model_path: str) -> str:
        """
        Load a model for inference.

        Args:
            model_type: Type of model
            model_path: Path to model file (.engine or .onnx)

        Returns:
            Model identifier
        """
        if not self._initialized:
            raise RuntimeError("Backend not initialized")

        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        model_id = f"{model_type.value}_{path.stem}"

        if path.suffix == ".engine" and self._mode == "tensorrt":
            await self._load_tensorrt_model(model_id, model_type, path)
        elif path.suffix == ".onnx":
            await self._load_onnx_model(model_id, model_type, path)
        else:
            raise ValueError(f"Unsupported model format: {path.suffix}")

        return model_id

    async def _load_tensorrt_model(
        self,
        model_id: str,
        model_type: ModelType,
        path: Path
    ) -> None:
        """Load a TensorRT engine."""
        with open(path, "rb") as f:
            engine_data = f.read()

        engine = self._trt_runtime.deserialize_cuda_engine(engine_data)
        if engine is None:
            raise RuntimeError(f"Failed to load TensorRT engine: {path}")

        context = engine.create_execution_context()

        self._trt_engines[model_id] = engine
        self._trt_contexts[model_id] = context
        self._model_info[model_id] = {
            "type": model_type,
            "path": str(path),
            "mode": "tensorrt",
            "input_shape": self._get_trt_input_shape(engine),
        }

        logger.info(f"Loaded TensorRT model: {model_id}")

    async def _load_onnx_model(
        self,
        model_id: str,
        model_type: ModelType,
        path: Path
    ) -> None:
        """Load an ONNX model with CUDA."""
        providers = [
            ("CUDAExecutionProvider", {
                "device_id": 0,
                "arena_extend_strategy": "kSameAsRequested",
                "gpu_mem_limit": 2 * 1024 * 1024 * 1024,  # 2GB limit
                "cudnn_conv_algo_search": "EXHAUSTIVE",
            }),
            "CPUExecutionProvider",
        ]

        session = ort.InferenceSession(
            str(path),
            self._ort_session_options,
            providers=providers
        )

        input_info = session.get_inputs()[0]
        output_info = session.get_outputs()

        self._ort_sessions[model_id] = session
        self._model_info[model_id] = {
            "type": model_type,
            "path": str(path),
            "mode": "onnx_cuda",
            "input_name": input_info.name,
            "input_shape": input_info.shape,
            "output_names": [o.name for o in output_info],
        }

        logger.info(f"Loaded ONNX-CUDA model: {model_id}")

    def _get_trt_input_shape(self, engine) -> List[int]:
        """Get input shape from TensorRT engine."""
        for i in range(engine.num_io_tensors):
            name = engine.get_tensor_name(i)
            if engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                return list(engine.get_tensor_shape(name))
        return [1, 3, 640, 640]  # Default

    async def unload_model(self, model_id: str) -> None:
        """Unload a model."""
        if model_id in self._trt_engines:
            del self._trt_contexts[model_id]
            del self._trt_engines[model_id]

        if model_id in self._ort_sessions:
            del self._ort_sessions[model_id]

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
        if model_id not in self._model_info:
            raise ValueError(f"Model not loaded: {model_id}")

        info = self._model_info[model_id]
        start_time = time.perf_counter()

        if info["mode"] == "tensorrt":
            outputs = await self._infer_tensorrt(model_id, input_data, info)
        else:
            outputs = await self._infer_onnx(model_id, input_data, info)

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

    async def _infer_tensorrt(
        self,
        model_id: str,
        input_data: np.ndarray,
        info: Dict[str, Any]
    ) -> List[np.ndarray]:
        """Run TensorRT inference."""
        engine = self._trt_engines[model_id]
        context = self._trt_contexts[model_id]

        # Preprocess
        input_tensor = self._preprocess(input_data, info["input_shape"])

        # Allocate buffers
        inputs = []
        outputs = []
        bindings = []

        for i in range(engine.num_io_tensors):
            name = engine.get_tensor_name(i)
            shape = engine.get_tensor_shape(name)
            dtype = trt.nptype(engine.get_tensor_dtype(name))
            size = trt.volume(shape)

            # Allocate device memory
            device_mem = cuda.mem_alloc(size * np.dtype(dtype).itemsize)

            if engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                # Copy input to device
                host_mem = np.ascontiguousarray(input_tensor)
                cuda.memcpy_htod(device_mem, host_mem)
                inputs.append((host_mem, device_mem))
            else:
                host_mem = np.empty(shape, dtype=dtype)
                outputs.append((host_mem, device_mem))

            bindings.append(int(device_mem))

        # Run inference
        context.execute_v2(bindings)

        # Copy outputs back
        result = []
        for host_mem, device_mem in outputs:
            cuda.memcpy_dtoh(host_mem, device_mem)
            result.append(host_mem)

        return result

    async def _infer_onnx(
        self,
        model_id: str,
        input_data: np.ndarray,
        info: Dict[str, Any]
    ) -> List[np.ndarray]:
        """Run ONNX Runtime with CUDA inference."""
        session = self._ort_sessions[model_id]

        # Preprocess
        input_tensor = self._preprocess(input_data, info["input_shape"])

        # Run inference
        outputs = session.run(
            info["output_names"],
            {info["input_name"]: input_tensor}
        )

        return outputs

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
    def gpu_name(self) -> str:
        """Get GPU name."""
        return self._gpu_name

    @property
    def gpu_memory_mb(self) -> int:
        """Get GPU memory in MB."""
        return self._gpu_memory_mb

    @property
    def mode(self) -> Optional[str]:
        """Get inference mode (tensorrt or onnx_cuda)."""
        return self._mode
