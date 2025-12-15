"""
Tests for croom.audio module.
"""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest


class TestAudioDeviceType:
    """Tests for AudioDeviceType enum."""

    def test_values(self):
        """Test audio device type values."""
        from croom.audio.device import AudioDeviceType

        assert AudioDeviceType.INPUT.value == "input"
        assert AudioDeviceType.OUTPUT.value == "output"


class TestAudioDeviceInfo:
    """Tests for AudioDeviceInfo dataclass."""

    def test_default_values(self):
        """Test default audio device info values."""
        from croom.audio.device import AudioDeviceInfo, AudioDeviceType

        info = AudioDeviceInfo(
            device_id="alsa_output.pci-0000_00_1f.3",
            name="Built-in Audio",
            device_type=AudioDeviceType.OUTPUT,
        )
        assert info.name == "Built-in Audio"
        assert info.device_type == AudioDeviceType.OUTPUT
        assert info.is_default is False

    def test_input_device(self):
        """Test input device info."""
        from croom.audio.device import AudioDeviceInfo, AudioDeviceType

        info = AudioDeviceInfo(
            device_id="alsa_input.usb-123",
            name="USB Microphone",
            device_type=AudioDeviceType.INPUT,
            is_default=True,
        )
        assert info.device_type == AudioDeviceType.INPUT
        assert info.is_default is True


class TestAudioService:
    """Tests for AudioService class."""

    @pytest.fixture
    def audio_service(self):
        """Create an audio service instance."""
        with patch("croom.audio.service.get_audio_devices", return_value=[]):
            from croom.audio.service import AudioService
            service = AudioService()
            return service

    def test_service_creation(self, audio_service):
        """Test audio service can be created."""
        assert audio_service is not None

    def test_service_with_config(self):
        """Test audio service with config."""
        with patch("croom.audio.service.get_audio_devices", return_value=[]):
            from croom.audio.service import AudioService
            config = {
                "input_device": "default",
                "output_device": "default",
                "sample_rate": 48000,
                "noise_reduction": True,
            }
            service = AudioService(config=config)
            assert service.config["sample_rate"] == 48000


class TestProcessorConfig:
    """Tests for audio processor configuration."""

    def test_processor_config_defaults(self):
        """Test processor config default values."""
        from croom.audio.processor import ProcessorConfig

        config = ProcessorConfig()
        assert config.sample_rate == 48000
        assert config.channels == 1
        assert config.enable_noise_reduction is True

    def test_processor_config_custom(self):
        """Test processor config custom values."""
        from croom.audio.processor import ProcessorConfig

        config = ProcessorConfig(
            sample_rate=44100,
            channels=2,
            enable_noise_reduction=False,
        )
        assert config.sample_rate == 44100
        assert config.channels == 2
        assert config.enable_noise_reduction is False


class TestNoiseReductionBackend:
    """Tests for NoiseReductionBackend enum."""

    def test_backend_values(self):
        """Test noise reduction backend values."""
        from croom.audio.processor import NoiseReductionBackend

        assert NoiseReductionBackend.RNNOISE.value == "rnnoise"
        assert NoiseReductionBackend.SPEEX.value == "speex"
