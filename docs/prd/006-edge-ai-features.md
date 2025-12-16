# PRD-006: Edge AI Features

## Document Information
| Field | Value |
|-------|-------|
| PRD ID | PRD-006 |
| Title | Edge AI Features for Video Conferencing |
| Author | Engineering Team |
| Created | 2025-12-15 |
| Status | Draft |
| Priority | P1 - High |
| Target Phase | Phase 2 |

---

## 1. Overview

### 1.1 Problem Statement
Modern video conferencing systems like Cisco Webex Room Kit offer AI-powered features:
- Automatic speaker tracking
- Intelligent participant framing
- Noise reduction
- Meeting insights

These features typically require expensive hardware ($3,000-15,000) or cloud processing (privacy concerns, latency, cost).

### 1.2 Solution
Implement edge AI features that run locally on Raspberry Pi hardware using:
- **Raspberry Pi 5 + AI Kit (Hailo-8L):** 13 TOPS, best performance
- **Raspberry Pi 4/5 + Coral USB:** 4 TOPS, widely available
- **Software-only mode:** CPU inference for basic features

### 1.3 Design Principles

1. **Privacy First:** All processing happens locally, no cloud dependency
2. **Hardware Adaptive:** Features scale based on available hardware
3. **Graceful Degradation:** Works without AI accelerator, just with fewer features
4. **Low Latency:** Real-time processing for meeting quality
5. **Energy Efficient:** Minimal impact on device temperature and power

### 1.4 Success Metrics
- Speaker tracking latency < 500ms
- Auto-framing accuracy > 90%
- Noise reduction: 10dB improvement
- CPU usage < 30% with accelerator
- User preference for AI features > 80%

---

## 2. Hardware Support Matrix

### 2.1 AI Acceleration Options

| Hardware | TOPS | Interface | Price | Availability | Status |
|----------|------|-----------|-------|--------------|--------|
| Raspberry Pi AI Kit (Hailo-8L) | 13 | M.2/PCIe | $70 | Pi 5 only | Primary |
| Coral USB Accelerator | 4 | USB 3.0 | $60 | Pi 4/5 | Secondary |
| Coral M.2 Accelerator | 4 | M.2 | $25 | Pi 5 | Secondary |
| CPU Only (Pi 5) | ~1 | N/A | $0 | Built-in | Fallback |
| CPU Only (Pi 4) | ~0.5 | N/A | $0 | Built-in | Fallback |

### 2.2 Feature Availability by Hardware

| Feature | AI Kit (13T) | Coral (4T) | Pi 5 CPU | Pi 4 CPU |
|---------|--------------|------------|----------|----------|
| Person Detection | ✓ 30fps | ✓ 15fps | ✓ 5fps | ✓ 2fps |
| Face Detection | ✓ 30fps | ✓ 15fps | ✓ 5fps | ✓ 2fps |
| Auto-Framing | ✓ Full | ✓ Basic | ✓ Basic | ○ Limited |
| Speaker Detection | ✓ Full | ✓ Full | ✓ Basic | ○ Limited |
| Pose Estimation | ✓ 25fps | ✓ 10fps | ○ 3fps | ✗ |
| Hand Raise Detection | ✓ Full | ✓ Full | ○ Basic | ✗ |
| Noise Reduction | ✓ Full | ✓ Full | ✓ Full | ✓ Full |
| Echo Cancellation | ✓ Full | ✓ Full | ✓ Full | ✓ Full |
| Occupancy Counting | ✓ Full | ✓ Full | ✓ Basic | ○ Limited |
| Gesture Recognition | ✓ Basic | ○ Limited | ✗ | ✗ |

Legend: ✓ = Full support, ○ = Limited, ✗ = Not supported

### 2.3 Camera Requirements

| Feature | Minimum | Recommended |
|---------|---------|-------------|
| Auto-Framing | 1080p fixed | 1080p+ |
| Speaker Tracking (PTZ) | USB PTZ camera | Logitech Rally, OBSBOT |
| Person Detection | 720p | 1080p |
| Hand Raise | 720p | 1080p |

---

## 3. AI Features Specification

### 3.1 Person Detection & Counting (P0)

**Description:** Detect and count people in the camera frame.

**Use Cases:**
- Room occupancy display
- Auto-start meeting when people enter
- Energy saving (turn off when empty)
- Analytics (room utilization)

**Technical Approach:**
- Model: YOLOv8n or MobileNet-SSD
- Input: 640x480 or 320x320 (depending on hardware)
- Output: Bounding boxes + count
- Target: 15-30 fps

**Implementation:**
```python
class PersonDetector:
    def __init__(self, accelerator='auto'):
        self.model = load_model('person_detection', accelerator)

    def detect(self, frame):
        # Returns list of person bounding boxes
        detections = self.model.infer(frame)
        return [d for d in detections if d.class_id == PERSON]

    def count(self, frame):
        return len(self.detect(frame))
```

**Privacy:**
- No face recognition or identification
- No data stored or transmitted
- Detection results only (count, positions)

---

### 3.2 Intelligent Auto-Framing (P0)

**Description:** Automatically crop and zoom the video to keep participants optimally framed.

**Modes:**
1. **Single Speaker:** Frame active speaker
2. **Group:** Frame all participants
3. **Dynamic:** Switch between modes automatically

**Technical Approach:**
- Combine person detection with face detection
- Calculate optimal crop region
- Smooth transitions (no jarring movements)
- Respect safe zones (head room, rule of thirds)

**Implementation:**
```python
class AutoFramer:
    def __init__(self):
        self.person_detector = PersonDetector()
        self.face_detector = FaceDetector()
        self.current_crop = None

    def calculate_frame(self, image):
        persons = self.person_detector.detect(image)
        faces = self.face_detector.detect(image)

        if len(faces) == 0:
            return self.default_frame()
        elif len(faces) == 1:
            return self.single_person_frame(faces[0])
        else:
            return self.group_frame(faces)

    def apply_smoothing(self, new_crop):
        # Smooth transition to avoid jarring movements
        if self.current_crop is None:
            self.current_crop = new_crop
        else:
            self.current_crop = lerp(self.current_crop, new_crop, 0.1)
        return self.current_crop
```

**Digital vs PTZ:**
| Type | Approach | Quality | Flexibility |
|------|----------|---------|-------------|
| Digital Zoom | Crop 4K/1080p source | Good (if 4K source) | Any camera |
| PTZ Camera | Physical pan/tilt/zoom | Excellent | PTZ camera required |

---

### 3.3 Active Speaker Detection (P1)

**Description:** Identify who is currently speaking to enable speaker tracking and framing.

**Technical Approach:**
- **Audio-based:** Voice activity detection (VAD)
- **Visual-based:** Lip movement detection
- **Combined:** Audio + visual for accuracy

**Implementation:**
```python
class SpeakerDetector:
    def __init__(self):
        self.vad = VoiceActivityDetector()
        self.face_detector = FaceDetector()
        self.lip_detector = LipMovementDetector()  # Optional

    def detect_speaker(self, audio_chunk, video_frame):
        # Check if someone is speaking (audio)
        is_speaking = self.vad.detect(audio_chunk)

        if is_speaking and video_frame is not None:
            faces = self.face_detector.detect(video_frame)
            if self.lip_detector:
                # Find face with lip movement
                for face in faces:
                    if self.lip_detector.is_moving(face):
                        return face
            # Fallback: return largest/center face
            return self.select_primary_face(faces)

        return None
```

**Use Cases:**
- Highlight active speaker in UI
- Automatic camera switching (if multiple cameras)
- Speaker tracking with PTZ camera
- Meeting analytics (speaking time)

---

### 3.4 PTZ Speaker Tracking (P1)

**Description:** Automatically control PTZ camera to follow the active speaker.

**Requirements:**
- PTZ camera with USB/VISCA/ONVIF control
- Speaker detection enabled
- Smooth movement algorithm

**Supported Cameras:**
| Camera | Control Protocol | Price | Notes |
|--------|-----------------|-------|-------|
| Logitech Rally | USB UVC PTZ | $1,300 | High quality |
| OBSBOT Tiny 2 | USB | $270 | AI built-in |
| PTZOptics | VISCA/ONVIF | $500+ | Pro options |
| Generic USB PTZ | UVC PTZ | $100-300 | Variable quality |

**Implementation:**
```python
class PTZController:
    def __init__(self, camera_type='uvc'):
        self.camera = self._init_camera(camera_type)
        self.speaker_detector = SpeakerDetector()
        self.current_target = None

    def track_speaker(self, audio, video):
        speaker_face = self.speaker_detector.detect_speaker(audio, video)

        if speaker_face:
            target = self._face_to_ptz_coords(speaker_face)
            self._smooth_move_to(target)

    def _smooth_move_to(self, target):
        # Implement smooth movement to avoid jarring
        # Use velocity-based control, not position jumps
        pass
```

**Movement Smoothing:**
- Minimum movement threshold (ignore small changes)
- Velocity-based control
- Acceleration/deceleration curves
- Dwell time before moving (avoid ping-ponging)

---

### 3.5 Noise Reduction (P0)

**Description:** Reduce background noise in microphone input.

**Technical Approach:**
- RNNoise (CPU-based, efficient)
- Or custom model on AI accelerator

**Noise Types Handled:**
- Keyboard typing
- HVAC noise
- Background chatter
- Fan noise
- Traffic/street noise

**Implementation:**
```python
class NoiseReducer:
    def __init__(self):
        # RNNoise is efficient enough for CPU
        self.rnnoise = RNNoise()

    def process(self, audio_chunk):
        return self.rnnoise.process(audio_chunk)
```

**Integration:**
- PulseAudio/PipeWire plugin
- Applied before sending to meeting platform
- User-adjustable strength (off, light, medium, aggressive)

---

### 3.6 Acoustic Echo Cancellation (P0)

**Description:** Remove echo from speaker audio feeding back into microphone.

**Technical Approach:**
- WebRTC AEC (proven, efficient)
- Speex DSP library
- PulseAudio module-echo-cancel

**Implementation:**
```bash
# PulseAudio echo cancellation
pactl load-module module-echo-cancel \
    source_name=echo_cancelled \
    source_master=@DEFAULT_SOURCE@ \
    sink_master=@DEFAULT_SINK@ \
    aec_method=webrtc
```

---

### 3.7 Hand Raise Detection (P2)

**Description:** Detect when participants raise their hand.

**Technical Approach:**
- Pose estimation (MediaPipe or custom)
- Hand position relative to head
- Gesture must be held for ~1 second

**Implementation:**
```python
class HandRaiseDetector:
    def __init__(self):
        self.pose_model = PoseEstimator()
        self.raise_threshold = 1.0  # seconds
        self.raised_hands = {}

    def detect(self, frame, timestamp):
        poses = self.pose_model.detect(frame)
        raised = []

        for i, pose in enumerate(poses):
            if self._is_hand_raised(pose):
                if i not in self.raised_hands:
                    self.raised_hands[i] = timestamp
                elif timestamp - self.raised_hands[i] > self.raise_threshold:
                    raised.append(i)
            else:
                self.raised_hands.pop(i, None)

        return raised

    def _is_hand_raised(self, pose):
        # Check if either wrist is above shoulder
        left_raised = pose.left_wrist.y < pose.left_shoulder.y
        right_raised = pose.right_wrist.y < pose.right_shoulder.y
        return left_raised or right_raised
```

**Use Cases:**
- Send notification to meeting host
- Display indicator in UI
- Meeting analytics

---

### 3.8 Room Occupancy Analytics (P2)

**Description:** Track room usage patterns for facilities management.

**Metrics:**
- Occupancy over time
- Peak usage hours
- Average meeting size
- Empty room time

**Implementation:**
```python
class OccupancyTracker:
    def __init__(self):
        self.person_detector = PersonDetector()
        self.history = []

    def record(self, frame, timestamp):
        count = self.person_detector.count(frame)
        self.history.append({
            'timestamp': timestamp,
            'count': count
        })
        # Aggregate and send to dashboard periodically
```

**Privacy:**
- Only count stored, no images
- No identification
- Aggregated data only sent to dashboard
- Local-only mode option

---

## 4. Software Architecture

### 4.1 AI Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      Camera Input (V4L2)                         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Frame Preprocessor                            │
│   (Resize, normalize, format conversion)                        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI Accelerator Dispatcher                     │
│   (Routes to Hailo, Coral, or CPU based on availability)        │
└─────────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Hailo Runtime   │ │  Coral EdgeTPU   │ │  TFLite CPU      │
│  (13 TOPS)       │ │  (4 TOPS)        │ │  (Fallback)      │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Feature Processors                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  Person     │ │   Face      │ │   Pose      │ │  Speaker  │ │
│  │  Detector   │ │  Detector   │ │  Estimator  │ │  Detector │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Action Handlers                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  Auto       │ │   PTZ       │ │  Hand Raise │ │ Occupancy │ │
│  │  Framing    │ │  Control    │ │  Alert      │ │  Tracker  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│               Output (Meeting, UI, Dashboard)                    │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Audio Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                  Microphone Input (ALSA/PulseAudio)              │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Echo Cancellation (AEC)                         │
│                  (WebRTC AEC / Speex)                           │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Noise Reduction (RNNoise)                       │
└─────────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│  Voice Activity Detection    │ │  To Meeting Platform         │
│  (Speaker Detection)         │ │  (Processed Audio)           │
└──────────────────────────────┘ └──────────────────────────────┘
```

### 4.3 Model Management

```python
class ModelManager:
    MODELS = {
        'person_detection': {
            'hailo': 'yolov8n_hailo.hef',
            'coral': 'ssd_mobilenet_v2_coco_quant_edgetpu.tflite',
            'cpu': 'ssd_mobilenet_v2.tflite'
        },
        'face_detection': {
            'hailo': 'retinaface_hailo.hef',
            'coral': 'ssd_mobilenet_v2_face_quant_edgetpu.tflite',
            'cpu': 'blazeface.tflite'
        },
        # ... more models
    }

    def __init__(self):
        self.accelerator = self._detect_accelerator()
        self.loaded_models = {}

    def _detect_accelerator(self):
        if self._check_hailo():
            return 'hailo'
        elif self._check_coral():
            return 'coral'
        else:
            return 'cpu'

    def load_model(self, model_name):
        if model_name not in self.loaded_models:
            model_path = self.MODELS[model_name][self.accelerator]
            self.loaded_models[model_name] = self._load(model_path)
        return self.loaded_models[model_name]
```

---

## 5. Performance Targets

### 5.1 Latency Targets

| Feature | Target | Maximum |
|---------|--------|---------|
| Person Detection | 33ms (30fps) | 100ms |
| Auto-Framing | 100ms | 200ms |
| Speaker Detection | 50ms | 150ms |
| PTZ Movement | 200ms | 500ms |
| Noise Reduction | 10ms | 20ms |

### 5.2 Resource Usage

| Mode | CPU Usage | Memory | Temperature |
|------|-----------|--------|-------------|
| AI Kit (full features) | <30% | <500MB | <65°C |
| Coral (full features) | <40% | <400MB | <60°C |
| CPU only (basic) | <60% | <300MB | <70°C |
| No AI | <20% | <200MB | <55°C |

### 5.3 Benchmarks Required

- [ ] FPS per feature per hardware
- [ ] End-to-end latency
- [ ] Resource usage monitoring
- [ ] Thermal throttling tests
- [ ] Extended operation (8+ hours)

---

## 6. Privacy & Security

### 6.1 Data Handling

| Data Type | Storage | Transmission | Retention |
|-----------|---------|--------------|-----------|
| Video frames | RAM only | Never | None |
| Detection results | RAM only | Optional (anon) | None |
| Occupancy counts | Local DB | Dashboard (anon) | 30 days |
| Model weights | Disk | Never | Permanent |

### 6.2 Privacy Mode

When enabled:
- All AI features disabled
- No frame processing
- Status LED indicates AI off
- Can be toggled via touch UI

### 6.3 Transparency

- Clear indicator when AI is active
- Settings show what features are enabled
- Documentation on what is processed
- No cloud dependency

---

## 7. Implementation Plan

### Phase 1: Foundation (Week 1-4)
- [ ] Hardware detection framework
- [ ] Model management system
- [ ] Person detection (all platforms)
- [ ] Basic auto-framing (digital zoom)
- [ ] Noise reduction integration

### Phase 2: Core Features (Week 5-8)
- [ ] Face detection
- [ ] Speaker detection (audio-based)
- [ ] Advanced auto-framing
- [ ] PTZ camera support (basic)

### Phase 3: Advanced Features (Week 9-12)
- [ ] Pose estimation
- [ ] Hand raise detection
- [ ] PTZ speaker tracking
- [ ] Occupancy analytics

### Phase 4: Polish (Week 13-16)
- [ ] Performance optimization
- [ ] Touch UI integration
- [ ] Dashboard integration
- [ ] Documentation
- [ ] Testing on all hardware

---

## 8. Testing Strategy

### 8.1 Test Scenarios

| Scenario | Test Method |
|----------|-------------|
| Single person | Automated + manual |
| Multiple people (2-10) | Automated + manual |
| Empty room | Automated |
| Low light | Manual |
| Movement/walking | Manual |
| Various backgrounds | Automated |
| Different cameras | Manual |

### 8.2 Accuracy Metrics

- Precision and recall for detection
- False positive/negative rates
- Framing quality (subjective + automated)
- Tracking smoothness

---

## 9. Open Questions

1. Which AI accelerator should be the primary target?
2. Should we support multiple accelerators simultaneously?
3. What is the minimum acceptable FPS for each feature?
4. Should occupancy data be sent to dashboard by default?
5. Do we need ONVIF support for enterprise PTZ cameras?

---

## 10. Success Criteria

- [ ] Person detection >95% accuracy
- [ ] Auto-framing preferred by >80% of users
- [ ] Speaker detection latency <500ms
- [ ] Noise reduction measurably improves audio quality
- [ ] All features work on target hardware
- [ ] No thermal throttling during normal operation

---

## 11. References

- [Raspberry Pi AI Kit Documentation](https://www.raspberrypi.com/products/ai-kit/)
- [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo)
- [Coral Models](https://coral.ai/models/)
- [RNNoise](https://github.com/xiph/rnnoise)
- [WebRTC AEC](https://webrtc.org/)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-15 | Claude | Initial PRD |
