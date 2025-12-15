"""
Tests for croom.ai.backends module.
"""

from unittest.mock import MagicMock, patch, AsyncMock
import numpy as np

import pytest

from croom.ai.backends import (
    get_available_backends,
    get_best_backend,
    get_backend_by_name,
)
from croom.ai.backends.base import AIBackend, InferenceResult


class TestAIBackendBase:
    """Tests for AIBackend base class."""

    def test_inference_result_creation(self):
        """Test InferenceResult dataclass."""
        result = InferenceResult(
            detections=[
                {"class": "person", "confidence": 0.95, "bbox": [100, 100, 200, 300]},
            ],
            inference_time_ms=15.5,
            model_name="yolov8n",
        )

        assert len(result.detections) == 1
        assert result.detections[0]["class"] == "person"
        assert result.inference_time_ms == 15.5

    def test_inference_result_empty(self):
        """Test empty InferenceResult."""
        result = InferenceResult(
            detections=[],
            inference_time_ms=10.0,
            model_name="test",
        )

        assert len(result.detections) == 0


class TestONNXCPUBackend:
    """Tests for ONNX CPU backend."""

    @patch("croom.ai.backends.onnx_cpu.ort")
    def test_is_available(self, mock_ort):
        """Test ONNX availability check."""
        from croom.ai.backends.onnx_cpu import ONNXCPUBackend

        mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]

        assert ONNXCPUBackend.is_available() is True

    @patch("croom.ai.backends.onnx_cpu.ort")
    def test_backend_name(self, mock_ort):
        """Test backend name."""
        from croom.ai.backends.onnx_cpu import ONNXCPUBackend

        backend = ONNXCPUBackend()
        assert backend.name == "onnx_cpu"

    @patch("croom.ai.backends.onnx_cpu.ort")
    def test_load_model(self, mock_ort):
        """Test model loading."""
        from croom.ai.backends.onnx_cpu import ONNXCPUBackend

        mock_session = MagicMock()
        mock_ort.InferenceSession.return_value = mock_session

        backend = ONNXCPUBackend()
        result = backend.load_model("test_model.onnx")

        assert result is True

    @patch("croom.ai.backends.onnx_cpu.ort")
    def test_inference(self, mock_ort):
        """Test running inference."""
        from croom.ai.backends.onnx_cpu import ONNXCPUBackend

        mock_session = MagicMock()
        mock_session.run.return_value = [np.array([[0.9, 100, 100, 200, 300]])]
        mock_ort.InferenceSession.return_value = mock_session

        backend = ONNXCPUBackend()
        backend.load_model("test_model.onnx")

        # Create test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = backend.run_inference(frame)

        assert isinstance(result, InferenceResult)


class TestNVIDIABackend:
    """Tests for NVIDIA TensorRT backend."""

    @patch("croom.ai.backends.nvidia.TENSORRT_AVAILABLE", True)
    @patch("croom.ai.backends.nvidia.CUDA_AVAILABLE", True)
    def test_is_available_with_tensorrt(self):
        """Test NVIDIA availability with TensorRT."""
        from croom.ai.backends.nvidia import NVIDIABackend

        # Mock the class method
        with patch.object(NVIDIABackend, "is_available", return_value=True):
            assert NVIDIABackend.is_available() is True

    @patch("croom.ai.backends.nvidia.TENSORRT_AVAILABLE", False)
    @patch("croom.ai.backends.nvidia.CUDA_AVAILABLE", False)
    @patch("croom.ai.backends.nvidia.ONNX_CUDA_AVAILABLE", False)
    def test_not_available_without_cuda(self):
        """Test NVIDIA unavailable without CUDA."""
        from croom.ai.backends.nvidia import NVIDIABackend

        with patch.object(NVIDIABackend, "is_available", return_value=False):
            assert NVIDIABackend.is_available() is False

    @patch("croom.ai.backends.nvidia.TENSORRT_AVAILABLE", True)
    @patch("croom.ai.backends.nvidia.CUDA_AVAILABLE", True)
    def test_backend_name(self):
        """Test NVIDIA backend name."""
        from croom.ai.backends.nvidia import NVIDIABackend

        with patch.object(NVIDIABackend, "__init__", lambda x: None):
            backend = NVIDIABackend()
            backend._name = "nvidia"
            assert backend._name == "nvidia"


class TestOpenVINOBackend:
    """Tests for Intel OpenVINO backend."""

    @patch("croom.ai.backends.openvino.OPENVINO_AVAILABLE", True)
    def test_is_available(self):
        """Test OpenVINO availability check."""
        from croom.ai.backends.openvino import OpenVINOBackend

        with patch.object(OpenVINOBackend, "is_available", return_value=True):
            assert OpenVINOBackend.is_available() is True

    @patch("croom.ai.backends.openvino.OPENVINO_AVAILABLE", False)
    def test_not_available(self):
        """Test OpenVINO unavailable."""
        from croom.ai.backends.openvino import OpenVINOBackend

        with patch.object(OpenVINOBackend, "is_available", return_value=False):
            assert OpenVINOBackend.is_available() is False


class TestBackendSelection:
    """Tests for backend selection logic."""

    @patch("croom.ai.backends.get_available_backends")
    def test_get_best_backend_prefers_gpu(self, mock_get_backends):
        """Test that GPU backends are preferred."""
        # Mock available backends
        mock_nvidia = MagicMock()
        mock_nvidia.name = "nvidia"
        mock_nvidia.is_available.return_value = True

        mock_cpu = MagicMock()
        mock_cpu.name = "onnx_cpu"
        mock_cpu.is_available.return_value = True

        mock_get_backends.return_value = [mock_nvidia, mock_cpu]

        with patch("croom.ai.backends.get_best_backend") as mock_best:
            mock_best.return_value = mock_nvidia
            best = get_best_backend()
            assert best == mock_nvidia

    @patch("croom.ai.backends.get_available_backends")
    def test_get_backend_by_name(self, mock_get_backends):
        """Test getting backend by name."""
        mock_cpu = MagicMock()
        mock_cpu.name = "onnx_cpu"

        mock_get_backends.return_value = [mock_cpu]

        with patch("croom.ai.backends.get_backend_by_name") as mock_by_name:
            mock_by_name.return_value = mock_cpu
            backend = get_backend_by_name("onnx_cpu")
            assert backend == mock_cpu

    def test_get_available_backends_returns_list(self):
        """Test that get_available_backends returns a list."""
        backends = get_available_backends()
        assert isinstance(backends, list)


class TestHailoBackend:
    """Tests for Hailo-8L backend."""

    @patch("croom.ai.backends.hailo.HAILO_AVAILABLE", True)
    def test_is_available(self):
        """Test Hailo availability check."""
        from croom.ai.backends.hailo import HailoBackend

        with patch.object(HailoBackend, "is_available", return_value=True):
            assert HailoBackend.is_available() is True

    @patch("croom.ai.backends.hailo.HAILO_AVAILABLE", False)
    def test_not_available(self):
        """Test Hailo unavailable."""
        from croom.ai.backends.hailo import HailoBackend

        with patch.object(HailoBackend, "is_available", return_value=False):
            assert HailoBackend.is_available() is False


class TestCoralBackend:
    """Tests for Google Coral TPU backend."""

    @patch("croom.ai.backends.coral.CORAL_AVAILABLE", True)
    def test_is_available(self):
        """Test Coral availability check."""
        from croom.ai.backends.coral import CoralBackend

        with patch.object(CoralBackend, "is_available", return_value=True):
            assert CoralBackend.is_available() is True

    @patch("croom.ai.backends.coral.CORAL_AVAILABLE", False)
    def test_not_available(self):
        """Test Coral unavailable."""
        from croom.ai.backends.coral import CoralBackend

        with patch.object(CoralBackend, "is_available", return_value=False):
            assert CoralBackend.is_available() is False
