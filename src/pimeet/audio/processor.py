"""
Audio processing pipeline for PiMeet.

Provides noise reduction, echo cancellation, and other DSP.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


class NoiseReductionBackend(Enum):
    """Available noise reduction backends."""
    RNNOISE = "rnnoise"           # RNNoise (lightweight RNN)
    DEEPFILTER = "deepfilter"     # DeepFilterNet (higher quality)
    SPEEX = "speex"               # Speex DSP (CPU efficient)
    NONE = "none"                 # No noise reduction


@dataclass
class ProcessorConfig:
    """Audio processor configuration."""
    sample_rate: int = 48000
    channels: int = 1
    frame_size: int = 480  # 10ms at 48kHz
    noise_reduction: bool = True
    noise_reduction_backend: NoiseReductionBackend = NoiseReductionBackend.RNNOISE
    noise_reduction_strength: float = 0.9  # 0.0 to 1.0
    echo_cancellation: bool = True
    auto_gain_control: bool = True
    vad_enabled: bool = True
    vad_threshold: float = 0.5


class AudioProcessor(ABC):
    """Base class for audio processors."""

    @abstractmethod
    async def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Process audio frame.

        Args:
            audio: Input audio as float32 numpy array

        Returns:
            Processed audio as float32 numpy array
        """
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Reset processor state."""
        pass


# Check for available backends
try:
    import rnnoise
    RNNOISE_AVAILABLE = True
except ImportError:
    RNNOISE_AVAILABLE = False

try:
    from df import enhance, init_df
    DEEPFILTER_AVAILABLE = True
except ImportError:
    DEEPFILTER_AVAILABLE = False

try:
    import speexdsp
    SPEEX_AVAILABLE = True
except ImportError:
    SPEEX_AVAILABLE = False


class NoiseReduction(AudioProcessor):
    """
    Noise reduction processor.

    Supports multiple backends:
    - RNNoise: Fast, RNN-based noise suppression (recommended for Pi)
    - DeepFilterNet: Higher quality, more CPU intensive
    - Speex: Traditional DSP, very lightweight
    """

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or ProcessorConfig()
        self._backend = None
        self._backend_type = self.config.noise_reduction_backend
        self._initialized = False

        # RNNoise state
        self._rnnoise_state = None

        # DeepFilterNet state
        self._df_model = None
        self._df_state = None

        # Speex state
        self._speex_preprocess = None

        # Buffer for frame alignment
        self._buffer = np.array([], dtype=np.float32)

    async def initialize(self) -> bool:
        """Initialize the noise reduction backend."""
        backend = self._backend_type

        # Auto-select best available backend
        if backend == NoiseReductionBackend.RNNOISE and not RNNOISE_AVAILABLE:
            logger.warning("RNNoise not available, trying alternatives")
            backend = NoiseReductionBackend.SPEEX if SPEEX_AVAILABLE else NoiseReductionBackend.NONE

        if backend == NoiseReductionBackend.DEEPFILTER and not DEEPFILTER_AVAILABLE:
            logger.warning("DeepFilterNet not available, trying alternatives")
            backend = NoiseReductionBackend.RNNOISE if RNNOISE_AVAILABLE else NoiseReductionBackend.NONE

        if backend == NoiseReductionBackend.SPEEX and not SPEEX_AVAILABLE:
            logger.warning("Speex not available, trying alternatives")
            backend = NoiseReductionBackend.RNNOISE if RNNOISE_AVAILABLE else NoiseReductionBackend.NONE

        try:
            if backend == NoiseReductionBackend.RNNOISE and RNNOISE_AVAILABLE:
                self._rnnoise_state = rnnoise.create_denoiser()
                self._backend_type = backend
                logger.info("Initialized RNNoise noise reduction")

            elif backend == NoiseReductionBackend.DEEPFILTER and DEEPFILTER_AVAILABLE:
                self._df_model, self._df_state, _ = init_df()
                self._backend_type = backend
                logger.info("Initialized DeepFilterNet noise reduction")

            elif backend == NoiseReductionBackend.SPEEX and SPEEX_AVAILABLE:
                self._speex_preprocess = speexdsp.Preprocessor(
                    self.config.frame_size,
                    self.config.sample_rate
                )
                self._speex_preprocess.denoise = True
                self._speex_preprocess.dereverb = True
                self._backend_type = backend
                logger.info("Initialized Speex noise reduction")

            else:
                self._backend_type = NoiseReductionBackend.NONE
                logger.warning("No noise reduction backend available")

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize noise reduction: {e}")
            self._backend_type = NoiseReductionBackend.NONE
            self._initialized = True
            return False

    async def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through noise reduction."""
        if not self._initialized:
            await self.initialize()

        if self._backend_type == NoiseReductionBackend.NONE:
            return audio

        try:
            # Ensure float32
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)

            # Flatten if multi-channel
            if len(audio.shape) > 1:
                audio = audio.flatten()

            if self._backend_type == NoiseReductionBackend.RNNOISE:
                return await self._process_rnnoise(audio)
            elif self._backend_type == NoiseReductionBackend.DEEPFILTER:
                return await self._process_deepfilter(audio)
            elif self._backend_type == NoiseReductionBackend.SPEEX:
                return await self._process_speex(audio)
            else:
                return audio

        except Exception as e:
            logger.error(f"Noise reduction error: {e}")
            return audio

    async def _process_rnnoise(self, audio: np.ndarray) -> np.ndarray:
        """Process using RNNoise."""
        # RNNoise expects 480 samples (10ms at 48kHz)
        frame_size = 480

        # Add to buffer
        self._buffer = np.concatenate([self._buffer, audio])

        output = []
        while len(self._buffer) >= frame_size:
            frame = self._buffer[:frame_size]
            self._buffer = self._buffer[frame_size:]

            # RNNoise expects int16
            frame_int16 = (frame * 32767).astype(np.int16)
            processed = rnnoise.process_frame(self._rnnoise_state, frame_int16)
            output.append(processed.astype(np.float32) / 32767.0)

        if output:
            return np.concatenate(output)
        return np.array([], dtype=np.float32)

    async def _process_deepfilter(self, audio: np.ndarray) -> np.ndarray:
        """Process using DeepFilterNet."""
        # Run in thread pool as it's CPU intensive
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: enhance(self._df_model, self._df_state, audio)
        )
        return result

    async def _process_speex(self, audio: np.ndarray) -> np.ndarray:
        """Process using Speex DSP."""
        frame_size = self.config.frame_size

        # Add to buffer
        self._buffer = np.concatenate([self._buffer, audio])

        output = []
        while len(self._buffer) >= frame_size:
            frame = self._buffer[:frame_size]
            self._buffer = self._buffer[frame_size:]

            # Speex expects int16
            frame_int16 = (frame * 32767).astype(np.int16)
            processed = self._speex_preprocess.run(frame_int16)
            output.append(processed.astype(np.float32) / 32767.0)

        if output:
            return np.concatenate(output)
        return np.array([], dtype=np.float32)

    async def reset(self) -> None:
        """Reset processor state."""
        self._buffer = np.array([], dtype=np.float32)

        if self._rnnoise_state:
            rnnoise.destroy_denoiser(self._rnnoise_state)
            self._rnnoise_state = rnnoise.create_denoiser()

    def __del__(self):
        """Cleanup resources."""
        if self._rnnoise_state and RNNOISE_AVAILABLE:
            try:
                rnnoise.destroy_denoiser(self._rnnoise_state)
            except Exception:
                pass


class EchoCancellation(AudioProcessor):
    """
    Acoustic Echo Cancellation (AEC).

    Removes speaker audio from microphone input to prevent feedback.
    """

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or ProcessorConfig()
        self._initialized = False
        self._speex_echo = None
        self._reference_buffer: List[np.ndarray] = []

    async def initialize(self) -> bool:
        """Initialize echo cancellation."""
        if not SPEEX_AVAILABLE:
            logger.warning("Speex not available, echo cancellation disabled")
            return False

        try:
            # Speex echo canceller
            frame_size = self.config.frame_size
            filter_length = frame_size * 10  # 100ms tail length

            self._speex_echo = speexdsp.Echo(
                frame_size,
                filter_length,
                self.config.sample_rate,
            )

            self._initialized = True
            logger.info("Initialized Speex echo cancellation")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize echo cancellation: {e}")
            return False

    async def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through echo canceller."""
        if not self._initialized or not self._speex_echo:
            return audio

        try:
            # Get reference audio (speaker output)
            if not self._reference_buffer:
                return audio

            reference = self._reference_buffer.pop(0)

            # Ensure same size
            min_len = min(len(audio), len(reference))
            audio = audio[:min_len]
            reference = reference[:min_len]

            # Convert to int16
            audio_int16 = (audio * 32767).astype(np.int16)
            ref_int16 = (reference * 32767).astype(np.int16)

            # Cancel echo
            processed = self._speex_echo.cancel(audio_int16, ref_int16)

            return processed.astype(np.float32) / 32767.0

        except Exception as e:
            logger.error(f"Echo cancellation error: {e}")
            return audio

    def add_reference(self, audio: np.ndarray) -> None:
        """
        Add speaker audio as reference for cancellation.

        Call this with the audio being played through speakers.
        """
        self._reference_buffer.append(audio.copy())

        # Limit buffer size
        while len(self._reference_buffer) > 10:
            self._reference_buffer.pop(0)

    async def reset(self) -> None:
        """Reset echo canceller state."""
        self._reference_buffer.clear()
        if self._speex_echo:
            # Reinitialize
            await self.initialize()


class AutoGainControl(AudioProcessor):
    """
    Automatic Gain Control (AGC).

    Normalizes audio levels for consistent volume.
    """

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or ProcessorConfig()
        self._target_level = 0.3  # Target RMS level
        self._max_gain = 10.0     # Maximum gain multiplier
        self._min_gain = 0.1     # Minimum gain multiplier
        self._current_gain = 1.0
        self._attack = 0.01      # Fast attack
        self._release = 0.001    # Slow release

    async def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply automatic gain control."""
        if len(audio) == 0:
            return audio

        try:
            # Calculate RMS
            rms = np.sqrt(np.mean(audio ** 2))

            if rms > 0.001:  # Avoid division by zero
                # Calculate desired gain
                desired_gain = self._target_level / rms
                desired_gain = np.clip(desired_gain, self._min_gain, self._max_gain)

                # Smooth gain changes
                if desired_gain > self._current_gain:
                    self._current_gain += (desired_gain - self._current_gain) * self._attack
                else:
                    self._current_gain += (desired_gain - self._current_gain) * self._release

            # Apply gain
            output = audio * self._current_gain

            # Soft clip to prevent distortion
            output = np.tanh(output)

            return output.astype(np.float32)

        except Exception as e:
            logger.error(f"AGC error: {e}")
            return audio

    async def reset(self) -> None:
        """Reset AGC state."""
        self._current_gain = 1.0


class VoiceActivityDetector(AudioProcessor):
    """
    Voice Activity Detection (VAD).

    Detects presence of speech in audio.
    """

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or ProcessorConfig()
        self._threshold = config.vad_threshold if config else 0.5
        self._is_speech = False
        self._speech_frames = 0
        self._silence_frames = 0
        self._hangover = 10  # Frames to keep active after speech

        # Energy-based VAD
        self._energy_history: List[float] = []
        self._history_size = 100

    @property
    def is_speech(self) -> bool:
        """Whether speech is currently detected."""
        return self._is_speech

    async def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Detect voice activity.

        Returns the input unchanged but updates is_speech state.
        """
        if len(audio) == 0:
            return audio

        try:
            # Calculate frame energy
            energy = np.sqrt(np.mean(audio ** 2))

            # Update history
            self._energy_history.append(energy)
            if len(self._energy_history) > self._history_size:
                self._energy_history.pop(0)

            # Adaptive threshold
            if len(self._energy_history) > 10:
                noise_floor = np.percentile(self._energy_history, 10)
                adaptive_threshold = noise_floor * 3 + 0.01
            else:
                adaptive_threshold = 0.02

            # Detect speech
            speech_detected = energy > adaptive_threshold

            if speech_detected:
                self._speech_frames += 1
                self._silence_frames = 0
                if self._speech_frames > 2:  # Require multiple frames
                    self._is_speech = True
            else:
                self._silence_frames += 1
                if self._silence_frames > self._hangover:
                    self._is_speech = False
                    self._speech_frames = 0

            return audio

        except Exception as e:
            logger.error(f"VAD error: {e}")
            return audio

    async def reset(self) -> None:
        """Reset VAD state."""
        self._is_speech = False
        self._speech_frames = 0
        self._silence_frames = 0
        self._energy_history.clear()


class AudioProcessingPipeline:
    """
    Complete audio processing pipeline.

    Chains multiple processors together.
    """

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or ProcessorConfig()
        self._processors: List[AudioProcessor] = []
        self._vad: Optional[VoiceActivityDetector] = None

    async def initialize(self) -> None:
        """Initialize the processing pipeline."""
        # Add processors based on config
        if self.config.noise_reduction:
            nr = NoiseReduction(self.config)
            await nr.initialize()
            self._processors.append(nr)

        if self.config.echo_cancellation:
            aec = EchoCancellation(self.config)
            if await aec.initialize():
                self._processors.append(aec)

        if self.config.auto_gain_control:
            agc = AutoGainControl(self.config)
            self._processors.append(agc)

        if self.config.vad_enabled:
            self._vad = VoiceActivityDetector(self.config)
            self._processors.append(self._vad)

        logger.info(f"Audio pipeline initialized with {len(self._processors)} processors")

    async def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through all processors."""
        result = audio

        for processor in self._processors:
            result = await processor.process(result)

        return result

    async def reset(self) -> None:
        """Reset all processors."""
        for processor in self._processors:
            await processor.reset()

    @property
    def is_speech(self) -> bool:
        """Whether VAD detects speech."""
        return self._vad.is_speech if self._vad else False

    def get_echo_canceller(self) -> Optional[EchoCancellation]:
        """Get echo canceller for reference audio."""
        for processor in self._processors:
            if isinstance(processor, EchoCancellation):
                return processor
        return None
