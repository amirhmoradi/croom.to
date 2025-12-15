# PRD-008: Cross-Platform Architecture

## Document Information
| Field | Value |
|-------|-------|
| PRD ID | PRD-008 |
| Title | Cross-Platform Architecture & Hardware Abstraction |
| Author | Engineering Team |
| Created | 2025-12-15 |
| Status | Draft |
| Priority | P0 - Critical |
| Target Phase | Phase 1 (Foundation) |

---

## 1. Overview

### 1.1 Problem Statement
PiMeet needs to support multiple hardware platforms:
- **Raspberry Pi 5** (primary) - ARM64, limited compute, edge AI accelerators
- **Raspberry Pi 4** (secondary) - ARM64, more limited
- **Ubuntu/Debian PCs** (future) - x86_64, powerful GPUs for AI

Without proper abstraction, we would need separate codebases or significant refactoring later.

### 1.2 Solution
Design a hardware abstraction layer from day 1 that:
- Abstracts AI acceleration (Hailo, Coral, NVIDIA, CPU)
- Abstracts platform-specific features (GPIO, HDMI-CEC)
- Uses common formats (ONNX models, V4L2 cameras)
- Enables single codebase for all platforms

### 1.3 Approach
**Pi-First with Abstraction:**
- Phase 1: Implement for Raspberry Pi 5 with full abstraction layer
- Phase 2: Add PC backends (NVIDIA, OpenVINO) without code changes

---

## 2. Supported Platforms

### 2.1 Phase 1 (Current)

| Platform | Architecture | AI Accelerators | Status |
|----------|--------------|-----------------|--------|
| Raspberry Pi 5 | arm64 | Hailo-8L, Coral USB, CPU | Primary |
| Raspberry Pi 4B | arm64 | Coral USB, CPU | Secondary |

### 2.2 Phase 2 (Future)

| Platform | Architecture | AI Accelerators | Status |
|----------|--------------|-----------------|--------|
| Ubuntu 22.04/24.04 | amd64 | NVIDIA GPU, Intel, CPU | Planned |
| Debian 12/13 | amd64 | NVIDIA GPU, Intel, CPU | Planned |

---

## 3. Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                           │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │   Touch UI  │  │   Agent     │  │  Dashboard  │             │
│   │   (Qt6)     │  │  (Python)   │  │  (Web)      │             │
│   └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                    Service Layer                                 │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │  Meeting    │  │     AI      │  │   Config    │             │
│   │  Service    │  │   Service   │  │   Service   │             │
│   └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                  Hardware Abstraction Layer                      │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │   Display   │  │    Audio    │  │   Camera    │             │
│   │  Abstract   │  │   Abstract  │  │  Abstract   │             │
│   └─────────────┘  └─────────────┘  └─────────────┘             │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │     AI      │  │   Network   │  │   System    │             │
│   │  Abstract   │  │   Abstract  │  │  Abstract   │             │
│   └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                    Platform Backends                             │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │ Raspberry Pi: Hailo, Coral, PiCamera, GPIO, HDMI-CEC      │ │
│   └───────────────────────────────────────────────────────────┘ │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │ PC (Future): NVIDIA/CUDA, OpenVINO, V4L2, ALSA            │ │
│   └───────────────────────────────────────────────────────────┘ │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │ Common: ONNX Runtime (CPU), PulseAudio, V4L2              │ │
│   └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 AI Abstraction Layer

```python
# Abstract interface for AI inference
class AIBackend(ABC):
    """Abstract base class for AI acceleration backends."""

    @abstractmethod
    def get_name(self) -> str:
        """Return backend name (e.g., 'hailo', 'coral', 'nvidia', 'cpu')."""
        pass

    @abstractmethod
    def get_capabilities(self) -> dict:
        """Return backend capabilities (TOPS, supported ops, etc.)."""
        pass

    @abstractmethod
    def load_model(self, model_path: str, model_type: str) -> Any:
        """Load a model for inference."""
        pass

    @abstractmethod
    def infer(self, model: Any, input_data: np.ndarray) -> np.ndarray:
        """Run inference on input data."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available on current hardware."""
        pass


class AIService:
    """High-level AI service that selects best available backend."""

    def __init__(self):
        self.backends = self._discover_backends()
        self.active_backend = self._select_best_backend()

    def _discover_backends(self) -> List[AIBackend]:
        """Discover available AI backends."""
        backends = []

        # Try each backend in priority order
        for backend_class in [HailoBackend, CoralBackend, NvidiaBackend, CPUBackend]:
            try:
                backend = backend_class()
                if backend.is_available():
                    backends.append(backend)
            except Exception:
                pass

        return backends

    def _select_best_backend(self) -> AIBackend:
        """Select the best available backend based on capabilities."""
        if not self.backends:
            raise RuntimeError("No AI backends available")

        # Sort by TOPS (performance)
        return max(self.backends, key=lambda b: b.get_capabilities().get('tops', 0))
```

### 3.3 Platform Detection

```python
class PlatformDetector:
    """Detect current platform and capabilities."""

    @staticmethod
    def detect() -> PlatformInfo:
        info = PlatformInfo()

        # Detect architecture
        info.arch = platform.machine()  # 'aarch64' or 'x86_64'

        # Detect OS
        info.os = platform.system()
        info.os_release = distro.id()  # 'raspbian', 'ubuntu', 'debian'

        # Detect Raspberry Pi model
        if os.path.exists('/proc/device-tree/model'):
            with open('/proc/device-tree/model') as f:
                model = f.read()
                if 'Raspberry Pi 5' in model:
                    info.device = 'rpi5'
                elif 'Raspberry Pi 4' in model:
                    info.device = 'rpi4'
        else:
            info.device = 'pc'

        # Detect AI accelerators
        info.ai_accelerators = []
        if HailoBackend.probe():
            info.ai_accelerators.append('hailo')
        if CoralBackend.probe():
            info.ai_accelerators.append('coral')
        if NvidiaBackend.probe():
            info.ai_accelerators.append('nvidia')

        return info
```

---

## 4. Component Abstractions

### 4.1 Camera Abstraction

```python
class CameraBackend(ABC):
    @abstractmethod
    def list_devices(self) -> List[CameraDevice]:
        pass

    @abstractmethod
    def open(self, device_id: str) -> CameraStream:
        pass

    @abstractmethod
    def capture_frame(self, stream: CameraStream) -> np.ndarray:
        pass

# Implementations
class V4L2CameraBackend(CameraBackend):
    """Works on both Pi and PC via Video4Linux2."""
    pass

class PiCameraBackend(CameraBackend):
    """Pi-specific camera module support."""
    pass
```

### 4.2 Audio Abstraction

```python
class AudioBackend(ABC):
    @abstractmethod
    def list_input_devices(self) -> List[AudioDevice]:
        pass

    @abstractmethod
    def list_output_devices(self) -> List[AudioDevice]:
        pass

    @abstractmethod
    def set_default_input(self, device_id: str):
        pass

# Single implementation works everywhere
class PulseAudioBackend(AudioBackend):
    """PulseAudio/PipeWire backend - works on Pi and PC."""
    pass
```

### 4.3 Display Abstraction

```python
class DisplayBackend(ABC):
    @abstractmethod
    def list_displays(self) -> List[Display]:
        pass

    @abstractmethod
    def set_power(self, display_id: str, on: bool):
        pass

class HDMICECBackend(DisplayBackend):
    """HDMI-CEC control - Pi primary, some PCs supported."""
    pass

class DDCBackend(DisplayBackend):
    """DDC/CI control - PC primary."""
    pass
```

---

## 5. Model Management

### 5.1 Model Format Strategy

```
                    Source Model
                    (PyTorch/TF)
                         │
                         ▼
                    ONNX Export
                    (Common Format)
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
   Hailo Compiler   TensorRT      ONNX Runtime
   (→ HEF file)     (→ engine)    (→ CPU/GPU)
         │               │               │
         ▼               ▼               ▼
    Pi + AI Kit       PC + NVIDIA      Fallback
```

### 5.2 Model Registry

```python
class ModelRegistry:
    """Manages models for different backends."""

    MODELS = {
        'person_detection': {
            'onnx': 'models/yolov8n.onnx',
            'hailo': 'models/yolov8n_hailo.hef',
            'coral': 'models/yolov8n_edgetpu.tflite',
            'tensorrt': 'models/yolov8n.engine',
        },
        'face_detection': {
            'onnx': 'models/retinaface.onnx',
            'hailo': 'models/retinaface_hailo.hef',
            # ... etc
        },
        'noise_reduction': {
            'cpu': 'rnnoise',  # CPU-only, works everywhere
        }
    }

    def get_model_path(self, model_name: str, backend: str) -> str:
        """Get appropriate model file for backend."""
        return self.MODELS[model_name].get(backend)
```

---

## 6. Package Structure

### 6.1 Python Package Layout

```
pimeet/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── agent.py              # Main agent
│   ├── config.py             # Configuration
│   └── service.py            # Service management
├── platform/
│   ├── __init__.py
│   ├── detector.py           # Platform detection
│   ├── capabilities.py       # Capability queries
│   └── backends/
│       ├── __init__.py
│       ├── base.py           # Abstract bases
│       ├── raspberry_pi.py   # Pi-specific
│       └── pc.py             # PC-specific (future)
├── ai/
│   ├── __init__.py
│   ├── service.py            # AI service
│   ├── models.py             # Model registry
│   └── backends/
│       ├── __init__.py
│       ├── base.py           # Abstract AI backend
│       ├── hailo.py          # Hailo-8L backend
│       ├── coral.py          # Coral EdgeTPU
│       ├── onnx_cpu.py       # ONNX Runtime CPU
│       └── nvidia.py         # NVIDIA (future)
├── meeting/
│   ├── __init__.py
│   ├── service.py            # Meeting service
│   └── providers/
│       ├── __init__.py
│       ├── base.py           # Abstract provider
│       ├── google_meet.py
│       ├── teams.py
│       └── zoom.py
├── audio/
│   ├── __init__.py
│   ├── service.py
│   └── backends/
│       ├── pulseaudio.py
│       └── pipewire.py
├── video/
│   ├── __init__.py
│   ├── service.py
│   └── backends/
│       ├── v4l2.py
│       └── picamera.py
└── display/
    ├── __init__.py
    ├── service.py
    └── backends/
        ├── hdmi_cec.py
        └── ddc.py
```

---

## 7. Configuration

### 7.1 Platform-Aware Configuration

```yaml
# /etc/pimeet/config.yaml
version: 2

platform:
  # Auto-detected, can be overridden
  type: auto  # 'rpi5', 'rpi4', 'pc', 'auto'

ai:
  # Backend selection
  backend: auto  # 'hailo', 'coral', 'nvidia', 'cpu', 'auto'

  # Features to enable
  features:
    person_detection: true
    noise_reduction: true
    auto_framing: true
    occupancy_counting: true

audio:
  backend: auto  # 'pulseaudio', 'pipewire', 'auto'
  noise_reduction: true
  echo_cancellation: true

video:
  backend: auto  # 'v4l2', 'picamera', 'auto'
  device: auto

display:
  backend: auto  # 'hdmi_cec', 'ddc', 'none'
  touch_display: auto
```

---

## 8. Build & Distribution

### 8.1 Package Builds

```yaml
# Build matrix
packages:
  - name: pimeet
    architectures:
      - arm64   # Raspberry Pi
      - amd64   # PC (future)
    distributions:
      - bookworm
      - trixie
      - jammy   # Ubuntu 22.04
      - noble   # Ubuntu 24.04
```

### 8.2 CI/CD Pipeline

```yaml
# .github/workflows/build.yml
jobs:
  build:
    strategy:
      matrix:
        arch: [arm64]  # Add amd64 in Phase 2
        distro: [bookworm, trixie]

    steps:
      - uses: actions/checkout@v4
      - name: Build package
        run: |
          ./scripts/build-package.sh ${{ matrix.arch }} ${{ matrix.distro }}
      - name: Upload to repo
        run: |
          ./scripts/upload-package.sh
```

---

## 9. Testing Strategy

### 9.1 Abstraction Tests

```python
# Test that all backends implement interface correctly
@pytest.mark.parametrize("backend_class", [
    HailoBackend,
    CoralBackend,
    CPUBackend,
])
def test_backend_interface(backend_class):
    backend = backend_class()

    # All backends must implement these
    assert hasattr(backend, 'get_name')
    assert hasattr(backend, 'get_capabilities')
    assert hasattr(backend, 'load_model')
    assert hasattr(backend, 'infer')
    assert hasattr(backend, 'is_available')
```

### 9.2 Hardware Matrix Testing

| Test | Pi 5 + Hailo | Pi 5 + Coral | Pi 4 | PC (Future) |
|------|-------------|--------------|------|-------------|
| Person detection | ✓ | ✓ | ✓ | Planned |
| Noise reduction | ✓ | ✓ | ✓ | Planned |
| Auto-framing | ✓ | ✓ | ✓ | Planned |
| Camera capture | ✓ | ✓ | ✓ | Planned |
| Audio processing | ✓ | ✓ | ✓ | Planned |

---

## 10. Migration Path

### 10.1 Adding New Platform

To add PC support in Phase 2:

1. **Add NVIDIA backend:**
   ```python
   # pimeet/ai/backends/nvidia.py
   class NvidiaBackend(AIBackend):
       def is_available(self):
           return torch.cuda.is_available()
   ```

2. **Add amd64 to build matrix**

3. **No changes to:**
   - Application layer
   - Service layer
   - Configuration format

---

## 11. Success Criteria

- [ ] All Pi features work through abstraction layer
- [ ] Backend selection is automatic and correct
- [ ] Adding new backend requires no app changes
- [ ] Configuration format is platform-agnostic
- [ ] Tests pass on all supported platforms

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-15 | Claude | Initial PRD |
