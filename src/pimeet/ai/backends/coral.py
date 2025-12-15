"""
Google Coral EdgeTPU backend.

Provides accelerated inference using Google Coral USB or M.2 TPU (4 TOPS).
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

# TensorFlow Lite and EdgeTPU runtime
try:
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    try:
        import tensorflow.lite as tflite
        TFLITE_AVAILABLE = True
    except ImportError:
        TFLITE_AVAILABLE = False
        tflite = None

# Check for EdgeTPU delegate
EDGETPU_AVAILABLE = False
if TFLITE_AVAILABLE:
    try:
        from tflite_runtime.interpreter import load_delegate
        # Try to load the delegate to verify EdgeTPU is available
        delegate = load_delegate("libedgetpu.so.1")
        EDGETPU_AVAILABLE = True
    except Exception:
        try:
            from pycoral.utils.edgetpu import make_interpreter
            EDGETPU_AVAILABLE = True
        except ImportError:
            pass


class CoralBackend(AIBackend):
    """
    Google Coral EdgeTPU backend for accelerated inference.

    Uses TensorFlow Lite with EdgeTPU delegate.
    Supports _edgetpu.tflite models compiled for Coral.
    """

    # Default model paths (EdgeTPU TFLite format)
    MODEL_PATHS = {
        ModelType.PERSON_DETECTION: "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite",
        ModelType.FACE_DETECTION: "models/ssd_mobilenet_v2_face_quant_postprocess_edgetpu.tflite",
    }

    def __init__(self):
        super().__init__()
        self._interpreters: Dict[str, Any] = {}
        self._model_info: Dict[str, Dict[str, Any]] = {}
        self._delegate = None

    @property
    def name(self) -> str:
        return "coral"

    def get_capabilities(self) -> AICapabilities:
        return AICapabilities(
            name="coral",
            tops=4.0,  # Coral EdgeTPU is 4 TOPS
            supported_models=[
                ModelType.PERSON_DETECTION,
                ModelType.FACE_DETECTION,
            ],
            max_batch_size=1,  # EdgeTPU doesn't support batching
            supports_int8=True,
            supports_fp16=False,
            supports_fp32=False,  # EdgeTPU uses int8 only
        )

    @classmethod
    def is_available(cls) -> bool:
        """Check if Coral EdgeTPU is available."""
        if not TFLITE_AVAILABLE or not EDGETPU_AVAILABLE:
            return False

        # Check for EdgeTPU device
        try:
            # Look for USB or PCIe Coral
            import subprocess
            result = subprocess.run(
                ["lsusb"],
                capture_output=True,
                timeout=5
            )
            # Google Coral USB vendor ID
            if b"18d1:9302" in result.stdout or b"1a6e:089a" in result.stdout:
                return True

            # Check for PCIe device
            pcie_path = Path("/sys/bus/pci/devices")
            if pcie_path.exists():
                for device in pcie_path.iterdir():
                    vendor_path = device / "vendor"
                    if vendor_path.exists():
                        vendor = vendor_path.read_text().strip()
                        if vendor == "0x1ac1":  # Global Unichip Corp (Coral)
                            return True

            return False
        except Exception:
            return False

    @classmethod
    def probe(cls) -> bool:
        """Quick probe for Coral hardware."""
        # Check for Coral device files
        apex_devices = list(Path("/dev").glob("apex_*"))
        if apex_devices:
            return True

        # Check USB
        try:
            import subprocess
            result = subprocess.run(
                ["lsusb", "-d", "18d1:9302"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    async def initialize(self) -> None:
        """Initialize Coral EdgeTPU."""
        if not TFLITE_AVAILABLE:
            raise RuntimeError("TensorFlow Lite not installed")

        if not EDGETPU_AVAILABLE:
            raise RuntimeError("EdgeTPU runtime not available")

        try:
            # Load EdgeTPU delegate
            try:
                from tflite_runtime.interpreter import load_delegate
                self._delegate = load_delegate("libedgetpu.so.1")
            except Exception:
                from pycoral.utils.edgetpu import get_runtime_version
                logger.info(f"EdgeTPU runtime version: {get_runtime_version()}")

            self._initialized = True
            logger.info("Coral EdgeTPU backend initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Coral: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown Coral backend."""
        for model_id in list(self._interpreters.keys()):
            await self.unload_model(model_id)

        self._delegate = None
        self._initialized = False
        logger.info("Coral backend shutdown")

    def get_model_path(self, model_type: ModelType) -> Optional[str]:
        """Get default EdgeTPU model path."""
        return self.MODEL_PATHS.get(model_type)

    async def load_model(self, model_type: ModelType, model_path: str) -> str:
        """
        Load an EdgeTPU model.

        Args:
            model_type: Type of model
            model_path: Path to _edgetpu.tflite file

        Returns:
            Model identifier
        """
        if not self._initialized:
            raise RuntimeError("Backend not initialized")

        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        if "_edgetpu.tflite" not in model_path:
            logger.warning("Model may not be compiled for EdgeTPU")

        model_id = f"{model_type.value}_{Path(model_path).stem}"

        try:
            # Create interpreter with EdgeTPU delegate
            try:
                from pycoral.utils.edgetpu import make_interpreter
                interpreter = make_interpreter(model_path)
            except ImportError:
                interpreter = tflite.Interpreter(
                    model_path=model_path,
                    experimental_delegates=[self._delegate] if self._delegate else None
                )

            interpreter.allocate_tensors()

            # Get input/output details
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()

            self._interpreters[model_id] = interpreter
            self._model_info[model_id] = {
                "type": model_type,
                "path": model_path,
                "input_details": input_details,
                "output_details": output_details,
            }

            logger.info(f"Loaded Coral model: {model_id}")
            return model_id

        except Exception as e:
            logger.error(f"Failed to load Coral model {model_path}: {e}")
            raise

    async def unload_model(self, model_id: str) -> None:
        """Unload a model."""
        if model_id in self._interpreters:
            del self._interpreters[model_id]
            del self._model_info[model_id]
            logger.info(f"Unloaded Coral model: {model_id}")

    async def infer(
        self,
        model_id: str,
        input_data: np.ndarray,
        confidence_threshold: float = 0.5
    ) -> InferenceResult:
        """
        Run inference on Coral EdgeTPU.

        Args:
            model_id: Model identifier
            input_data: Input image (HWC, uint8, BGR)
            confidence_threshold: Minimum detection confidence

        Returns:
            InferenceResult with detections
        """
        if model_id not in self._interpreters:
            raise ValueError(f"Model not loaded: {model_id}")

        interpreter = self._interpreters[model_id]
        info = self._model_info[model_id]

        start_time = time.perf_counter()

        # Preprocess input
        input_tensor = self._preprocess(input_data, info["input_details"][0])

        # Set input tensor
        interpreter.set_tensor(info["input_details"][0]["index"], input_tensor)

        # Run inference
        interpreter.invoke()

        # Get outputs
        outputs = {}
        for output_detail in info["output_details"]:
            outputs[output_detail["name"]] = interpreter.get_tensor(output_detail["index"])

        # Postprocess
        detections = self._postprocess(
            outputs,
            info,
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
        input_detail: Dict[str, Any]
    ) -> np.ndarray:
        """Preprocess image for Coral input."""
        import cv2

        # Get input shape [batch, height, width, channels]
        shape = input_detail["shape"]
        target_h, target_w = shape[1], shape[2]

        # Resize
        resized = cv2.resize(image, (target_w, target_h))

        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Ensure uint8
        if rgb.dtype != np.uint8:
            rgb = rgb.astype(np.uint8)

        # Add batch dimension
        tensor = np.expand_dims(rgb, axis=0)

        return tensor

    def _postprocess(
        self,
        outputs: Dict[str, np.ndarray],
        model_info: Dict[str, Any],
        original_size: Tuple[int, int],
        confidence_threshold: float
    ) -> List[DetectionResult]:
        """Postprocess Coral SSD output."""
        detections = []
        output_details = model_info["output_details"]

        # Standard SSD MobileNet output format:
        # - boxes: [1, num_detections, 4] (y1, x1, y2, x2)
        # - classes: [1, num_detections]
        # - scores: [1, num_detections]
        # - count: [1]

        boxes = None
        classes = None
        scores = None

        for detail in output_details:
            name = detail["name"].lower()
            tensor = outputs[detail["name"]]

            if "box" in name or "location" in name:
                boxes = tensor
            elif "class" in name:
                classes = tensor
            elif "score" in name:
                scores = tensor

        if boxes is None or scores is None:
            return detections

        # Process detections
        for i in range(len(scores[0])):
            score = float(scores[0][i])
            if score < confidence_threshold:
                continue

            class_id = int(classes[0][i]) if classes is not None else 0

            # Only keep person detections (class 0 in COCO)
            if class_id != 0:
                continue

            # Get box coordinates (normalized)
            y1, x1, y2, x2 = boxes[0][i]

            detections.append(DetectionResult(
                class_id=class_id,
                class_name="person",
                confidence=score,
                bbox=(float(x1), float(y1), float(x2), float(y2))
            ))

        return detections


def get_coral_model_info():
    """
    Information about compiling models for Coral EdgeTPU.

    To compile TFLite models for EdgeTPU:
    1. Install Edge TPU Compiler
    2. Quantize model to int8 (full integer quantization)
    3. Run: edgetpu_compiler model.tflite

    Pre-compiled models available in Coral Model Zoo.
    """
    return {
        "compiler": "Edge TPU Compiler",
        "input_formats": [".tflite"],
        "output_format": "_edgetpu.tflite",
        "documentation": "https://coral.ai/docs/",
    }
