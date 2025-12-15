"""
Hailo-8L backend for Pi AI Kit.

Provides accelerated inference using the Hailo-8L NPU (13 TOPS).
This is the primary accelerator for Raspberry Pi 5.
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

# Hailo Runtime is only available on systems with Hailo hardware
try:
    from hailo_platform import (
        HEF,
        VDevice,
        HailoStreamInterface,
        ConfigureParams,
        InferVStreams,
        InputVStreamParams,
        OutputVStreamParams,
        FormatType,
    )
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False


class HailoBackend(AIBackend):
    """
    Hailo-8L backend for accelerated inference.

    Uses the Hailo Runtime to run inference on Hailo-8L NPU.
    Supports HEF (Hailo Executable Format) models.
    """

    # Default model paths (HEF format)
    MODEL_PATHS = {
        ModelType.PERSON_DETECTION: "models/yolov8n_hailo.hef",
        ModelType.FACE_DETECTION: "models/retinaface_hailo.hef",
        ModelType.POSE_ESTIMATION: "models/yolov8n_pose_hailo.hef",
    }

    def __init__(self):
        super().__init__()
        self._device = None
        self._hefs: Dict[str, Any] = {}
        self._networks: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "hailo"

    def get_capabilities(self) -> AICapabilities:
        return AICapabilities(
            name="hailo",
            tops=13.0,  # Hailo-8L is 13 TOPS
            supported_models=[
                ModelType.PERSON_DETECTION,
                ModelType.FACE_DETECTION,
                ModelType.POSE_ESTIMATION,
                ModelType.HAND_DETECTION,
            ],
            max_batch_size=8,
            supports_int8=True,
            supports_fp16=False,
            supports_fp32=False,  # Hailo uses int8 quantization
        )

    @classmethod
    def is_available(cls) -> bool:
        """Check if Hailo hardware is available."""
        if not HAILO_AVAILABLE:
            return False

        try:
            # Try to enumerate devices
            from hailo_platform import VDevice
            with VDevice() as device:
                return True
        except Exception:
            return False

    @classmethod
    def probe(cls) -> bool:
        """Quick probe for Hailo hardware."""
        # Check for Hailo device in /dev
        hailo_devices = list(Path("/dev").glob("hailo*"))
        return len(hailo_devices) > 0

    async def initialize(self) -> None:
        """Initialize Hailo device."""
        if not HAILO_AVAILABLE:
            raise RuntimeError("Hailo Runtime not installed")

        try:
            self._device = VDevice()
            logger.info("Hailo device initialized")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Hailo device: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown Hailo device."""
        # Unload all models
        for model_id in list(self._networks.keys()):
            await self.unload_model(model_id)

        if self._device:
            self._device = None

        self._initialized = False
        logger.info("Hailo backend shutdown")

    def get_model_path(self, model_type: ModelType) -> Optional[str]:
        """Get default HEF model path."""
        return self.MODEL_PATHS.get(model_type)

    async def load_model(self, model_type: ModelType, model_path: str) -> str:
        """
        Load a HEF model.

        Args:
            model_type: Type of model
            model_path: Path to .hef file

        Returns:
            Model identifier
        """
        if not self._initialized:
            raise RuntimeError("Backend not initialized")

        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        if not model_path.endswith(".hef"):
            raise ValueError("Hailo backend requires .hef model files")

        model_id = f"{model_type.value}_{Path(model_path).stem}"

        try:
            # Load HEF
            hef = HEF(model_path)
            self._hefs[model_id] = hef

            # Configure network group
            configure_params = ConfigureParams.create_from_hef(
                hef=hef,
                interface=HailoStreamInterface.PCIe
            )
            network_groups = self._device.configure(hef, configure_params)
            network_group = network_groups[0]

            # Get input/output info
            input_vstream_info = hef.get_input_vstream_infos()
            output_vstream_info = hef.get_output_vstream_infos()

            self._networks[model_id] = {
                "type": model_type,
                "hef": hef,
                "network_group": network_group,
                "input_info": input_vstream_info,
                "output_info": output_vstream_info,
            }

            logger.info(f"Loaded Hailo model: {model_id}")
            return model_id

        except Exception as e:
            logger.error(f"Failed to load Hailo model {model_path}: {e}")
            raise

    async def unload_model(self, model_id: str) -> None:
        """Unload a model."""
        if model_id in self._networks:
            del self._networks[model_id]
        if model_id in self._hefs:
            del self._hefs[model_id]
        logger.info(f"Unloaded Hailo model: {model_id}")

    async def infer(
        self,
        model_id: str,
        input_data: np.ndarray,
        confidence_threshold: float = 0.5
    ) -> InferenceResult:
        """
        Run inference on Hailo NPU.

        Args:
            model_id: Model identifier
            input_data: Input image (HWC, uint8, BGR)
            confidence_threshold: Minimum detection confidence

        Returns:
            InferenceResult with detections
        """
        if model_id not in self._networks:
            raise ValueError(f"Model not loaded: {model_id}")

        network = self._networks[model_id]
        hef = network["hef"]
        network_group = network["network_group"]

        start_time = time.perf_counter()

        # Preprocess input
        input_tensor = self._preprocess(input_data, network["input_info"])

        # Setup vstreams
        input_vstreams_params = InputVStreamParams.make_from_network_group(
            network_group,
            format_type=FormatType.UINT8
        )
        output_vstreams_params = OutputVStreamParams.make_from_network_group(
            network_group,
            format_type=FormatType.FLOAT32
        )

        # Run inference
        with InferVStreams(
            network_group,
            input_vstreams_params,
            output_vstreams_params
        ) as infer_pipeline:
            input_dict = {network["input_info"][0].name: input_tensor}
            outputs = infer_pipeline.infer(input_dict)

        # Postprocess
        detections = self._postprocess(
            outputs,
            network["type"],
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
        input_info: List[Any]
    ) -> np.ndarray:
        """Preprocess image for Hailo input."""
        import cv2

        # Get input shape from HEF
        shape = input_info[0].shape
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
        model_type: ModelType,
        original_size: Tuple[int, int],
        confidence_threshold: float
    ) -> List[DetectionResult]:
        """Postprocess Hailo outputs."""
        detections = []

        if model_type == ModelType.PERSON_DETECTION:
            # Hailo YOLOv8 output format
            for output_name, output_data in outputs.items():
                # Process detection output
                # Format depends on specific model export
                pass

        return detections


# Convenience function for model compilation info
def get_hailo_model_info():
    """
    Information about compiling models for Hailo.

    To compile ONNX models to HEF format:
    1. Install Hailo Dataflow Compiler (DFC)
    2. Run: hailo optimize <model.onnx> --hw-arch hailo8l
    3. Run: hailo compile <model.har> --hw-arch hailo8l

    Pre-compiled models available in Hailo Model Zoo.
    """
    return {
        "compiler": "Hailo Dataflow Compiler",
        "input_formats": [".onnx", ".pt", ".pb"],
        "output_format": ".hef",
        "documentation": "https://hailo.ai/developer-zone/",
    }
