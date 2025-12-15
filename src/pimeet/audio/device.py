"""
Audio device abstraction for PiMeet.

Provides unified interface for audio devices across different systems.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
import numpy as np

logger = logging.getLogger(__name__)


class AudioDeviceType(Enum):
    """Type of audio device."""
    INPUT = "input"        # Microphone
    OUTPUT = "output"      # Speaker
    DUPLEX = "duplex"      # Both input and output


@dataclass
class AudioDeviceInfo:
    """Information about an audio device."""
    id: str
    name: str
    device_type: AudioDeviceType
    sample_rate: int = 48000
    channels: int = 1
    is_default: bool = False
    driver: str = "alsa"  # alsa, pulseaudio, pipewire
    hw_params: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_input(self) -> bool:
        return self.device_type in (AudioDeviceType.INPUT, AudioDeviceType.DUPLEX)

    @property
    def is_output(self) -> bool:
        return self.device_type in (AudioDeviceType.OUTPUT, AudioDeviceType.DUPLEX)


class AudioDevice(ABC):
    """Abstract base class for audio devices."""

    def __init__(self, device_info: AudioDeviceInfo):
        self.info = device_info
        self._running = False
        self._callbacks: List[Callable[[np.ndarray], None]] = []

    @property
    def is_running(self) -> bool:
        return self._running

    @abstractmethod
    async def open(self) -> bool:
        """Open the audio device."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the audio device."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start audio streaming."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop audio streaming."""
        pass

    @abstractmethod
    async def read(self, frames: int) -> Optional[np.ndarray]:
        """Read audio data from input device."""
        pass

    @abstractmethod
    async def write(self, data: np.ndarray) -> bool:
        """Write audio data to output device."""
        pass

    def on_audio(self, callback: Callable[[np.ndarray], None]) -> None:
        """Register callback for incoming audio data."""
        self._callbacks.append(callback)

    def _notify_callbacks(self, data: np.ndarray) -> None:
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Audio callback error: {e}")


# Try to import audio backends
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False


class SoundDeviceAudioDevice(AudioDevice):
    """Audio device using sounddevice library."""

    def __init__(self, device_info: AudioDeviceInfo):
        super().__init__(device_info)
        self._stream = None
        self._input_queue: asyncio.Queue = None
        self._dtype = np.float32

    async def open(self) -> bool:
        if not SOUNDDEVICE_AVAILABLE:
            logger.error("sounddevice library not available")
            return False

        try:
            self._input_queue = asyncio.Queue(maxsize=100)
            return True
        except Exception as e:
            logger.error(f"Failed to open audio device: {e}")
            return False

    async def close(self) -> None:
        await self.stop()
        self._input_queue = None

    async def start(self) -> None:
        if self._running:
            return

        try:
            device_id = int(self.info.id) if self.info.id.isdigit() else self.info.id

            if self.info.is_input:
                def input_callback(indata, frames, time, status):
                    if status:
                        logger.debug(f"Audio input status: {status}")
                    try:
                        if self._input_queue and not self._input_queue.full():
                            # Put without blocking
                            asyncio.get_event_loop().call_soon_threadsafe(
                                self._input_queue.put_nowait,
                                indata.copy()
                            )
                    except Exception as e:
                        logger.debug(f"Input queue error: {e}")

                self._stream = sd.InputStream(
                    device=device_id,
                    samplerate=self.info.sample_rate,
                    channels=self.info.channels,
                    dtype=self._dtype,
                    callback=input_callback,
                    blocksize=1024,
                )

            elif self.info.is_output:
                self._stream = sd.OutputStream(
                    device=device_id,
                    samplerate=self.info.sample_rate,
                    channels=self.info.channels,
                    dtype=self._dtype,
                    blocksize=1024,
                )

            self._stream.start()
            self._running = True
            logger.info(f"Audio device started: {self.info.name}")

        except Exception as e:
            logger.error(f"Failed to start audio device: {e}")
            raise

    async def stop(self) -> None:
        if not self._running:
            return

        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            self._running = False
            logger.info(f"Audio device stopped: {self.info.name}")

        except Exception as e:
            logger.error(f"Failed to stop audio device: {e}")

    async def read(self, frames: int = 1024) -> Optional[np.ndarray]:
        """Read audio data from input queue."""
        if not self._running or not self._input_queue:
            return None

        try:
            data = await asyncio.wait_for(
                self._input_queue.get(),
                timeout=1.0
            )
            self._notify_callbacks(data)
            return data
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Failed to read audio: {e}")
            return None

    async def write(self, data: np.ndarray) -> bool:
        """Write audio data to output stream."""
        if not self._running or not self._stream:
            return False

        try:
            self._stream.write(data)
            return True
        except Exception as e:
            logger.error(f"Failed to write audio: {e}")
            return False


class PyAudioDevice(AudioDevice):
    """Audio device using PyAudio library."""

    def __init__(self, device_info: AudioDeviceInfo):
        super().__init__(device_info)
        self._pa = None
        self._stream = None
        self._input_queue: asyncio.Queue = None
        self._format = None

    async def open(self) -> bool:
        if not PYAUDIO_AVAILABLE:
            logger.error("PyAudio library not available")
            return False

        try:
            self._pa = pyaudio.PyAudio()
            self._format = pyaudio.paFloat32
            self._input_queue = asyncio.Queue(maxsize=100)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")
            return False

    async def close(self) -> None:
        await self.stop()
        if self._pa:
            self._pa.terminate()
            self._pa = None
        self._input_queue = None

    async def start(self) -> None:
        if self._running or not self._pa:
            return

        try:
            device_index = int(self.info.id) if self.info.id.isdigit() else None

            if self.info.is_input:
                def input_callback(in_data, frame_count, time_info, status):
                    try:
                        data = np.frombuffer(in_data, dtype=np.float32)
                        if self._input_queue and not self._input_queue.full():
                            asyncio.get_event_loop().call_soon_threadsafe(
                                self._input_queue.put_nowait,
                                data
                            )
                    except Exception:
                        pass
                    return (None, pyaudio.paContinue)

                self._stream = self._pa.open(
                    format=self._format,
                    channels=self.info.channels,
                    rate=self.info.sample_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=1024,
                    stream_callback=input_callback,
                )

            elif self.info.is_output:
                self._stream = self._pa.open(
                    format=self._format,
                    channels=self.info.channels,
                    rate=self.info.sample_rate,
                    output=True,
                    output_device_index=device_index,
                    frames_per_buffer=1024,
                )

            self._stream.start_stream()
            self._running = True
            logger.info(f"PyAudio device started: {self.info.name}")

        except Exception as e:
            logger.error(f"Failed to start PyAudio device: {e}")
            raise

    async def stop(self) -> None:
        if not self._running:
            return

        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None

            self._running = False
            logger.info(f"PyAudio device stopped: {self.info.name}")

        except Exception as e:
            logger.error(f"Failed to stop PyAudio device: {e}")

    async def read(self, frames: int = 1024) -> Optional[np.ndarray]:
        if not self._running or not self._input_queue:
            return None

        try:
            data = await asyncio.wait_for(
                self._input_queue.get(),
                timeout=1.0
            )
            self._notify_callbacks(data)
            return data
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Failed to read audio: {e}")
            return None

    async def write(self, data: np.ndarray) -> bool:
        if not self._running or not self._stream:
            return False

        try:
            self._stream.write(data.astype(np.float32).tobytes())
            return True
        except Exception as e:
            logger.error(f"Failed to write audio: {e}")
            return False


def get_audio_devices() -> List[AudioDeviceInfo]:
    """
    Get list of available audio devices.

    Returns:
        List of AudioDeviceInfo for all available devices
    """
    devices = []

    # Try sounddevice first
    if SOUNDDEVICE_AVAILABLE:
        try:
            device_list = sd.query_devices()
            default_input = sd.default.device[0]
            default_output = sd.default.device[1]

            for idx, dev in enumerate(device_list):
                if dev['max_input_channels'] > 0:
                    devices.append(AudioDeviceInfo(
                        id=str(idx),
                        name=dev['name'],
                        device_type=AudioDeviceType.INPUT,
                        sample_rate=int(dev['default_samplerate']),
                        channels=min(dev['max_input_channels'], 2),
                        is_default=(idx == default_input),
                        driver="sounddevice",
                    ))

                if dev['max_output_channels'] > 0:
                    devices.append(AudioDeviceInfo(
                        id=str(idx),
                        name=dev['name'],
                        device_type=AudioDeviceType.OUTPUT,
                        sample_rate=int(dev['default_samplerate']),
                        channels=min(dev['max_output_channels'], 2),
                        is_default=(idx == default_output),
                        driver="sounddevice",
                    ))

            return devices

        except Exception as e:
            logger.warning(f"Failed to query sounddevice devices: {e}")

    # Fall back to PyAudio
    if PYAUDIO_AVAILABLE:
        try:
            pa = pyaudio.PyAudio()
            default_input = pa.get_default_input_device_info()['index']
            default_output = pa.get_default_output_device_info()['index']

            for idx in range(pa.get_device_count()):
                dev = pa.get_device_info_by_index(idx)

                if dev['maxInputChannels'] > 0:
                    devices.append(AudioDeviceInfo(
                        id=str(idx),
                        name=dev['name'],
                        device_type=AudioDeviceType.INPUT,
                        sample_rate=int(dev['defaultSampleRate']),
                        channels=min(dev['maxInputChannels'], 2),
                        is_default=(idx == default_input),
                        driver="pyaudio",
                    ))

                if dev['maxOutputChannels'] > 0:
                    devices.append(AudioDeviceInfo(
                        id=str(idx),
                        name=dev['name'],
                        device_type=AudioDeviceType.OUTPUT,
                        sample_rate=int(dev['defaultSampleRate']),
                        channels=min(dev['maxOutputChannels'], 2),
                        is_default=(idx == default_output),
                        driver="pyaudio",
                    ))

            pa.terminate()
            return devices

        except Exception as e:
            logger.warning(f"Failed to query PyAudio devices: {e}")

    logger.warning("No audio backend available")
    return devices


def create_audio_device(device_info: AudioDeviceInfo) -> AudioDevice:
    """
    Create an audio device instance.

    Args:
        device_info: Device information

    Returns:
        AudioDevice instance
    """
    if device_info.driver == "sounddevice" and SOUNDDEVICE_AVAILABLE:
        return SoundDeviceAudioDevice(device_info)
    elif device_info.driver == "pyaudio" and PYAUDIO_AVAILABLE:
        return PyAudioDevice(device_info)
    elif SOUNDDEVICE_AVAILABLE:
        return SoundDeviceAudioDevice(device_info)
    elif PYAUDIO_AVAILABLE:
        return PyAudioDevice(device_info)
    else:
        raise RuntimeError("No audio backend available")
