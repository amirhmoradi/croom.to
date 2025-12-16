---
title: Configuration
description: All configuration options for Croom devices.
order: 5
---

# Configuration Guide

Croom uses a YAML configuration file and environment variables for settings.

## Configuration File

The main configuration file is located at `/etc/croom/config.yaml`:

```yaml
# Basic Settings
device:
  name: "Conference Room A"
  location: "Building 1, Floor 2"
  timezone: "America/New_York"

# Display Settings
display:
  resolution: "1920x1080"
  orientation: "landscape"  # landscape, portrait, auto
  hdmi_cec: true
  standby_timeout: 300  # seconds

# Camera Settings
camera:
  device: "/dev/video0"
  resolution: "1920x1080"
  framerate: 30
  auto_exposure: true

# Audio Settings
audio:
  input_device: "default"
  output_device: "default"
  noise_reduction: true
  echo_cancellation: true
  input_volume: 80
  output_volume: 70

# AI Features
ai:
  enabled: true
  accelerator: "auto"  # hailo, coral, cpu, auto
  auto_framing: true
  speaker_detection: true
  person_detection: true

# Meeting Platforms
platforms:
  google_meet:
    enabled: true
  microsoft_teams:
    enabled: true
  zoom:
    enabled: true
  webex:
    enabled: true

# Calendar Integration
calendar:
  provider: "google"  # google, microsoft, none
  client_id: "your-client-id"
  auto_join: true
  join_before_minutes: 1

# Network Settings
network:
  hostname: "croom-room-a"
  wifi:
    ssid: "Corporate-WiFi"
    # password in secrets file
  proxy:
    enabled: false
    url: "http://proxy.example.com:8080"

# Fleet Management
management:
  enabled: true
  server: "https://fleet.croom.to"
  # api_key in secrets file

# Security
security:
  local_auth: true
  pin_required: false
  allowed_networks:
    - "10.0.0.0/8"
    - "192.168.0.0/16"
```

## Environment Variables

Environment variables override config file settings:

```bash
# Core Settings
CROOM_DEVICE_NAME="Conference Room A"
CROOM_TIMEZONE="America/New_York"

# Camera
CROOM_CAMERA_DEVICE="/dev/video0"
CROOM_CAMERA_RESOLUTION="1920x1080"

# Audio
CROOM_AUDIO_INPUT="default"
CROOM_AUDIO_OUTPUT="default"
CROOM_NOISE_REDUCTION="true"

# AI
CROOM_AI_ENABLED="true"
CROOM_AI_ACCELERATOR="hailo"
CROOM_AUTO_FRAMING="true"

# Calendar
CROOM_CALENDAR_PROVIDER="google"
CROOM_CALENDAR_AUTO_JOIN="true"

# Management
CROOM_MANAGEMENT_ENABLED="true"
CROOM_MANAGEMENT_SERVER="https://fleet.croom.to"
CROOM_MANAGEMENT_API_KEY="your-api-key"

# Debug
CROOM_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
CROOM_DEBUG="false"
```

## Secrets Management

Sensitive values should be stored in `/etc/croom/secrets.yaml`:

```yaml
# WiFi password
wifi_password: "your-wifi-password"

# Calendar OAuth credentials
calendar_client_secret: "your-oauth-secret"

# Fleet management API key
management_api_key: "your-api-key"

# Vexa transcription API key
vexa_api_key: "your-vexa-key"
```

Set proper permissions:

```bash
sudo chmod 600 /etc/croom/secrets.yaml
sudo chown root:root /etc/croom/secrets.yaml
```

## Camera Configuration

### USB Camera Settings

```yaml
camera:
  device: "/dev/video0"
  resolution: "1920x1080"  # or "1280x720", "3840x2160"
  framerate: 30
  format: "MJPEG"  # MJPEG, YUYV, H264

  # Manual adjustments
  brightness: 50      # 0-100
  contrast: 50        # 0-100
  saturation: 50      # 0-100
  auto_exposure: true
  auto_white_balance: true
```

### PTZ Camera Settings

```yaml
camera:
  type: "ptz"
  device: "/dev/video0"

  ptz:
    protocol: "visca"  # visca, onvif, http
    address: "192.168.1.100"
    port: 5678

    # Movement settings
    pan_speed: 10    # 1-24
    tilt_speed: 10   # 1-24
    zoom_speed: 5    # 1-7

    # Presets
    presets:
      home: 1
      whiteboard: 2
      podium: 3
```

## AI Configuration

### Auto-Framing

```yaml
ai:
  auto_framing:
    enabled: true
    mode: "group"       # single, group, speaker
    margin: 0.15        # Frame margin (0.0-0.5)
    smoothing: 0.3      # Movement smoothing (0.0-1.0)
    min_face_size: 0.05 # Minimum face size to detect

    # For PTZ cameras
    ptz_control: true
    preset_on_empty: "home"
```

### Speaker Detection

```yaml
ai:
  speaker_detection:
    enabled: true
    sensitivity: 0.7    # 0.0-1.0
    switch_delay: 2.0   # Seconds before switching
    highlight_speaker: true
```

### Noise Reduction

```yaml
ai:
  noise_reduction:
    enabled: true
    level: "moderate"   # light, moderate, aggressive
    preserve_music: false
```

## Calendar Integration

### Google Calendar

```yaml
calendar:
  provider: "google"
  client_id: "your-client-id.apps.googleusercontent.com"
  auto_join: true
  join_before_minutes: 1

  # Filter by calendar
  calendars:
    - "primary"
    - "room-a@company.com"

  # Filter by meeting types
  meeting_types:
    - "google_meet"
    - "zoom"
    - "teams"
```

### Microsoft 365

```yaml
calendar:
  provider: "microsoft"
  tenant_id: "your-tenant-id"
  client_id: "your-client-id"

  # Room resource account
  resource_email: "room-a@company.com"
```

## Display Configuration

### HDMI-CEC

```yaml
display:
  hdmi_cec:
    enabled: true
    turn_on_meeting_start: true
    turn_off_after_meeting: true
    standby_timeout: 300  # Seconds of inactivity

    # CEC device configuration
    device_type: "playback"  # playback, recording, tuner
    osd_name: "Croom"
```

### Touch Screen

```yaml
display:
  touch_screen:
    enabled: true
    device: "/dev/input/touchscreen"
    orientation: "normal"  # normal, inverted, left, right

    # Calibration
    calibration:
      min_x: 0
      max_x: 4095
      min_y: 0
      max_y: 4095
```

## Network Configuration

### Static IP

```yaml
network:
  mode: "static"
  ip_address: "192.168.1.100"
  netmask: "255.255.255.0"
  gateway: "192.168.1.1"
  dns:
    - "8.8.8.8"
    - "8.8.4.4"
```

### WiFi with Enterprise Auth

```yaml
network:
  wifi:
    ssid: "Corporate-WiFi"
    security: "wpa-enterprise"
    eap_method: "peap"
    identity: "croom-device"
    # password in secrets file
```

### Proxy Settings

```yaml
network:
  proxy:
    enabled: true
    http: "http://proxy.example.com:8080"
    https: "http://proxy.example.com:8080"
    no_proxy:
      - "localhost"
      - "127.0.0.1"
      - "*.local"
```

## Applying Configuration Changes

After editing configuration:

```bash
# Validate configuration
sudo croom config validate

# Apply changes
sudo systemctl restart croom

# Check status
sudo systemctl status croom
```

## Next Steps

- [Meeting Platforms](/docs/platforms/) - Platform-specific setup
- [AI Features](/docs/ai-features/) - Configure AI capabilities
- [Fleet Management](/docs/management/) - Centralized configuration
