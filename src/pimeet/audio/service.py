"""
Audio Service for PiMeet.

High-level audio management with device handling and processing.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
import numpy as np

from pimeet.audio.device import (
    AudioDevice,
    AudioDeviceInfo,
    AudioDeviceType,
    get_audio_devices,
    create_audio_device,
)
from pimeet.audio.processor import (
    ProcessorConfig,
    NoiseReductionBackend,
    AudioProcessingPipeline,
)

logger = logging.getLogger(__name__)


class AudioService:
    """
    High-level audio service for PiMeet.

    Manages audio devices, processing pipeline, and audio routing.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize audio service.

        Args:
            config: Service configuration with:
                - input_device: Input device ID or 'default'
                - output_device: Output device ID or 'default'
                - sample_rate: Audio sample rate (default 48000)
                - channels: Number of channels (default 1)
                - noise_reduction: Enable noise reduction (default True)
                - noise_backend: Noise reduction backend ('rnnoise', 'deepfilter', 'speex')
                - echo_cancellation: Enable AEC (default True)
                - auto_gain: Enable AGC (default True)
        """
        self.config = config or {}

        # Devices
        self._input_device: Optional[AudioDevice] = None
        self._output_device: Optional[AudioDevice] = None
        self._available_devices: List[AudioDeviceInfo] = []

        # Processing
        self._pipeline: Optional[AudioProcessingPipeline] = None
        self._processor_config: Optional[ProcessorConfig] = None

        # State
        self._running = False
        self._muted = False
        self._volume = 1.0

        # Callbacks
        self._on_audio: List[Callable[[np.ndarray], None]] = []
        self._on_level: List[Callable[[float], None]] = []
        self._on_speech: List[Callable[[bool], None]] = []

        # Audio routing
        self._audio_task: Optional[asyncio.Task] = None
        self._last_speech_state = False

    async def initialize(self) -> bool:
        """
        Initialize the audio service.

        Returns:
            True if initialization successful
        """
        try:
            # Discover devices
            self._available_devices = get_audio_devices()
            logger.info(f"Found {len(self._available_devices)} audio devices")

            # Setup processor config
            sample_rate = self.config.get('sample_rate', 48000)
            channels = self.config.get('channels', 1)

            noise_backend_str = self.config.get('noise_backend', 'rnnoise')
            noise_backend = {
                'rnnoise': NoiseReductionBackend.RNNOISE,
                'deepfilter': NoiseReductionBackend.DEEPFILTER,
                'speex': NoiseReductionBackend.SPEEX,
                'none': NoiseReductionBackend.NONE,
            }.get(noise_backend_str, NoiseReductionBackend.RNNOISE)

            self._processor_config = ProcessorConfig(
                sample_rate=sample_rate,
                channels=channels,
                noise_reduction=self.config.get('noise_reduction', True),
                noise_reduction_backend=noise_backend,
                echo_cancellation=self.config.get('echo_cancellation', True),
                auto_gain_control=self.config.get('auto_gain', True),
                vad_enabled=self.config.get('vad', True),
            )

            # Initialize processing pipeline
            self._pipeline = AudioProcessingPipeline(self._processor_config)
            await self._pipeline.initialize()

            # Setup input device
            input_id = self.config.get('input_device', 'default')
            if not await self._setup_input_device(input_id):
                logger.warning("No input device configured")

            # Setup output device
            output_id = self.config.get('output_device', 'default')
            if not await self._setup_output_device(output_id):
                logger.warning("No output device configured")

            logger.info("Audio service initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize audio service: {e}")
            return False

    async def _setup_input_device(self, device_id: str) -> bool:
        """Setup input (microphone) device."""
        try:
            device_info = self._find_device(device_id, AudioDeviceType.INPUT)
            if not device_info:
                return False

            self._input_device = create_audio_device(device_info)
            if not await self._input_device.open():
                logger.error(f"Failed to open input device: {device_info.name}")
                return False

            logger.info(f"Input device: {device_info.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to setup input device: {e}")
            return False

    async def _setup_output_device(self, device_id: str) -> bool:
        """Setup output (speaker) device."""
        try:
            device_info = self._find_device(device_id, AudioDeviceType.OUTPUT)
            if not device_info:
                return False

            self._output_device = create_audio_device(device_info)
            if not await self._output_device.open():
                logger.error(f"Failed to open output device: {device_info.name}")
                return False

            logger.info(f"Output device: {device_info.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to setup output device: {e}")
            return False

    def _find_device(
        self,
        device_id: str,
        device_type: AudioDeviceType
    ) -> Optional[AudioDeviceInfo]:
        """Find a device by ID or return default."""
        matching = [
            d for d in self._available_devices
            if d.device_type == device_type
        ]

        if not matching:
            return None

        # Handle 'default'
        if device_id == 'default':
            default = next((d for d in matching if d.is_default), None)
            return default or matching[0]

        # Find by ID
        for device in matching:
            if device.id == device_id:
                return device

        # Fallback to default
        return matching[0]

    async def start(self) -> None:
        """Start audio capture and processing."""
        if self._running:
            return

        self._running = True

        # Start input device
        if self._input_device:
            await self._input_device.start()
            self._audio_task = asyncio.create_task(self._audio_loop())

        # Start output device
        if self._output_device:
            await self._output_device.start()

        logger.info("Audio service started")

    async def stop(self) -> None:
        """Stop audio capture and processing."""
        if not self._running:
            return

        self._running = False

        # Stop audio task
        if self._audio_task:
            self._audio_task.cancel()
            try:
                await self._audio_task
            except asyncio.CancelledError:
                pass
            self._audio_task = None

        # Stop devices
        if self._input_device:
            await self._input_device.stop()

        if self._output_device:
            await self._output_device.stop()

        logger.info("Audio service stopped")

    async def _audio_loop(self) -> None:
        """Main audio processing loop."""
        while self._running:
            try:
                # Read from input
                audio = await self._input_device.read()
                if audio is None or len(audio) == 0:
                    continue

                # Process audio
                if self._pipeline and not self._muted:
                    processed = await self._pipeline.process(audio)
                else:
                    processed = audio if not self._muted else np.zeros_like(audio)

                # Apply volume
                processed = processed * self._volume

                # Calculate level
                level = float(np.sqrt(np.mean(processed ** 2)))
                for callback in self._on_level:
                    try:
                        callback(level)
                    except Exception:
                        pass

                # Check speech state
                if self._pipeline:
                    is_speech = self._pipeline.is_speech
                    if is_speech != self._last_speech_state:
                        self._last_speech_state = is_speech
                        for callback in self._on_speech:
                            try:
                                callback(is_speech)
                            except Exception:
                                pass

                # Notify listeners
                for callback in self._on_audio:
                    try:
                        callback(processed)
                    except Exception:
                        pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Audio loop error: {e}")
                await asyncio.sleep(0.01)

    async def play(self, audio: np.ndarray) -> bool:
        """
        Play audio through the output device.

        Args:
            audio: Audio data as float32 numpy array

        Returns:
            True if playback started successfully
        """
        if not self._output_device:
            return False

        try:
            # Provide reference for echo cancellation
            if self._pipeline:
                aec = self._pipeline.get_echo_canceller()
                if aec:
                    aec.add_reference(audio)

            # Apply volume
            audio = audio * self._volume

            return await self._output_device.write(audio)

        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
            return False

    def mute(self) -> None:
        """Mute the microphone."""
        self._muted = True
        logger.debug("Microphone muted")

    def unmute(self) -> None:
        """Unmute the microphone."""
        self._muted = False
        logger.debug("Microphone unmuted")

    def toggle_mute(self) -> bool:
        """
        Toggle mute state.

        Returns:
            New mute state (True if muted)
        """
        self._muted = not self._muted
        return self._muted

    @property
    def is_muted(self) -> bool:
        """Whether microphone is muted."""
        return self._muted

    @property
    def volume(self) -> float:
        """Current volume level (0.0 to 1.0)."""
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        """Set volume level."""
        self._volume = max(0.0, min(1.0, value))
        logger.debug(f"Volume set to {self._volume:.1%}")

    @property
    def is_speech(self) -> bool:
        """Whether speech is currently detected."""
        return self._pipeline.is_speech if self._pipeline else False

    @property
    def devices(self) -> List[AudioDeviceInfo]:
        """Get list of available audio devices."""
        return self._available_devices.copy()

    def get_input_devices(self) -> List[AudioDeviceInfo]:
        """Get list of input (microphone) devices."""
        return [d for d in self._available_devices if d.is_input]

    def get_output_devices(self) -> List[AudioDeviceInfo]:
        """Get list of output (speaker) devices."""
        return [d for d in self._available_devices if d.is_output]

    async def set_input_device(self, device_id: str) -> bool:
        """
        Change the input device.

        Args:
            device_id: Device ID to switch to

        Returns:
            True if switch successful
        """
        was_running = self._running

        if self._input_device:
            await self._input_device.stop()
            await self._input_device.close()

        if not await self._setup_input_device(device_id):
            return False

        if was_running and self._input_device:
            await self._input_device.start()

        return True

    async def set_output_device(self, device_id: str) -> bool:
        """
        Change the output device.

        Args:
            device_id: Device ID to switch to

        Returns:
            True if switch successful
        """
        was_running = self._running

        if self._output_device:
            await self._output_device.stop()
            await self._output_device.close()

        if not await self._setup_output_device(device_id):
            return False

        if was_running and self._output_device:
            await self._output_device.start()

        return True

    def on_audio(self, callback: Callable[[np.ndarray], None]) -> None:
        """Register callback for processed audio data."""
        self._on_audio.append(callback)

    def on_level(self, callback: Callable[[float], None]) -> None:
        """Register callback for audio level updates."""
        self._on_level.append(callback)

    def on_speech(self, callback: Callable[[bool], None]) -> None:
        """Register callback for speech detection changes."""
        self._on_speech.append(callback)

    async def shutdown(self) -> None:
        """Shutdown the audio service."""
        await self.stop()

        if self._input_device:
            await self._input_device.close()
            self._input_device = None

        if self._output_device:
            await self._output_device.close()
            self._output_device = None

        if self._pipeline:
            await self._pipeline.reset()
            self._pipeline = None

        self._on_audio.clear()
        self._on_level.clear()
        self._on_speech.clear()

        logger.info("Audio service shutdown")


def create_audio_service(config: Dict[str, Any]) -> AudioService:
    """
    Create an audio service from configuration.

    Args:
        config: Audio configuration dict

    Returns:
        Configured AudioService instance
    """
    return AudioService(config)
