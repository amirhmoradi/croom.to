---
title: Touch Screen Interface
description: Configure and customize the Croom touch screen room controller.
order: 7
---

# Touch Screen Interface

Croom includes a beautiful Qt6-based touch screen interface for room control.

## Overview

The touch screen provides:

- Meeting controls (join, leave, mute, camera)
- Calendar view with upcoming meetings
- Room status display
- Quick settings access
- Custom branding options

## Hardware Setup

### Official Raspberry Pi Display

```bash
# Enable DSI display
sudo raspi-config nonint do_blanking 0

# Configure in config.txt
sudo nano /boot/firmware/config.txt
```

Add:
```
# Official 7" display
dtoverlay=vc4-kms-dsi-7inch
```

### USB Touchscreens

Most USB touchscreens work automatically. For calibration:

```bash
# Install calibration tool
sudo apt install xinput-calibrator

# Run calibration
xinput_calibrator

# Save calibration
sudo nano /etc/X11/xorg.conf.d/99-calibration.conf
```

### HDMI Touchscreens

```yaml
display:
  touch_screen:
    enabled: true
    device: "/dev/input/event0"
    type: "usb"

    # For inverted screens
    orientation: "inverted"
```

## Interface Configuration

### Basic Settings

```yaml
touch_screen:
  enabled: true

  # Appearance
  theme: "dark"          # dark, light, auto
  accent_color: "#6366f1"
  font_size: "medium"    # small, medium, large

  # Behavior
  screen_timeout: 60     # Seconds to dim
  wake_on_motion: true   # PIR sensor support

  # Layout
  clock_format: "12h"    # 12h, 24h
  show_seconds: false
  show_weather: true
```

### Custom Branding

```yaml
touch_screen:
  branding:
    # Logo (PNG, SVG supported)
    logo: "/etc/croom/assets/company-logo.png"
    logo_height: 48

    # Colors
    primary_color: "#6366f1"
    background_color: "#0f172a"
    text_color: "#f8fafc"

    # Custom CSS
    custom_css: "/etc/croom/assets/custom.css"
```

### Screen Layout

```yaml
touch_screen:
  layout:
    # Home screen widgets
    home:
      - type: "clock"
        position: "top-center"
      - type: "calendar"
        position: "left"
        show_next: 3
      - type: "room_status"
        position: "right"
      - type: "quick_join"
        position: "bottom"

    # Meeting screen
    meeting:
      show_controls: true
      show_participants: true
      show_chat: false
```

## Home Screen

### Clock Widget

Displays current time and date:

```yaml
widgets:
  clock:
    format: "HH:mm"
    show_date: true
    date_format: "dddd, MMMM d"
```

### Calendar Widget

Shows upcoming meetings:

```yaml
widgets:
  calendar:
    max_events: 5
    show_time: true
    show_organizer: false
    join_button: true

    # Highlight current meeting
    highlight_current: true

    # Filter events
    filter:
      minimum_duration: 5  # Minutes
      require_video_link: true
```

### Room Status Widget

Shows current room state:

```yaml
widgets:
  room_status:
    show_occupancy: true
    show_next_meeting: true
    show_availability: true

    # Status colors
    available_color: "#22c55e"
    busy_color: "#ef4444"
    soon_busy_color: "#f59e0b"
```

### Quick Join Widget

For joining ad-hoc meetings:

```yaml
widgets:
  quick_join:
    enabled: true
    platforms:
      - "google_meet"
      - "zoom"
      - "teams"
    show_recent: true
    max_recent: 5
```

## Meeting Controls

During a meeting, the touch screen shows:

### Audio Controls

```yaml
meeting_controls:
  audio:
    mute_button: true
    volume_slider: true
    noise_reduction_toggle: true
    audio_device_selector: true
```

### Video Controls

```yaml
meeting_controls:
  video:
    camera_toggle: true
    camera_selector: true
    auto_framing_toggle: true

    # PTZ controls (if available)
    ptz:
      enabled: true
      presets: true
      manual_control: true
```

### Meeting Actions

```yaml
meeting_controls:
  actions:
    leave_meeting: true
    share_screen: false  # Not typically used on room devices
    raise_hand: true
    reactions: true
    chat: false
```

## Settings Panel

Accessible via the gear icon:

```yaml
settings_panel:
  # Visible settings
  sections:
    - "audio"
    - "video"
    - "display"
    - "network"
    - "about"

  # Protected settings (require PIN)
  protected:
    - "network"
    - "factory_reset"

  # Admin PIN
  admin_pin: "1234"  # Store in secrets file
```

## Screensaver & Power Saving

```yaml
display:
  power_saving:
    enabled: true
    dim_after: 60      # Seconds
    dim_level: 20      # Percent
    sleep_after: 300   # Seconds

    # Wake triggers
    wake_on_touch: true
    wake_on_motion: true  # Requires PIR sensor
    wake_on_meeting: true

  screensaver:
    enabled: true
    type: "clock"      # clock, blank, custom
    custom_image: "/etc/croom/assets/screensaver.png"
```

## Accessibility

```yaml
touch_screen:
  accessibility:
    high_contrast: false
    large_text: false
    reduce_motion: false
    screen_reader: false

    # Touch accommodations
    touch_hold_delay: 0.5  # Seconds
    ignore_repeat: true
```

## Multi-Display Setup

For rooms with multiple screens:

```yaml
displays:
  primary:
    device: "HDMI-1"
    role: "meeting"      # Shows meeting content

  secondary:
    device: "DSI-1"
    role: "controller"   # Touch screen interface

  tertiary:
    device: "HDMI-2"
    role: "signage"      # Digital signage when idle
```

## Development & Customization

### Custom Themes

Create a theme file at `/etc/croom/themes/custom.qss`:

```css
/* Custom Qt stylesheet */
QMainWindow {
    background-color: #0f172a;
}

QPushButton {
    background-color: #6366f1;
    border-radius: 8px;
    padding: 12px 24px;
    color: white;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #4f46e5;
}

QPushButton:pressed {
    background-color: #4338ca;
}
```

Apply the theme:

```yaml
touch_screen:
  theme: "custom"
  theme_path: "/etc/croom/themes/custom.qss"
```

### Custom Widgets

Extend the interface with custom widgets:

```python
# /etc/croom/widgets/custom_widget.py
from croom.ui.widgets import BaseWidget

class CustomWidget(BaseWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Widget implementation
```

Register in config:

```yaml
touch_screen:
  custom_widgets:
    - path: "/etc/croom/widgets/custom_widget.py"
      class: "CustomWidget"
      position: "bottom-right"
```

## Troubleshooting

### Touch not responding

```bash
# Check touch device
sudo cat /proc/bus/input/devices | grep -A5 touch

# Test touch input
sudo evtest /dev/input/event0

# Recalibrate
xinput_calibrator
```

### Display not showing

```bash
# Check display connection
tvservice -s

# Check Qt display
export QT_QPA_PLATFORM=eglfs
croom ui test
```

### UI performance issues

```yaml
# Enable hardware acceleration
touch_screen:
  renderer: "opengl"    # opengl, software
  vsync: true
  fps_limit: 60
```

## Next Steps

- [AI Features](/docs/ai-features/) - Auto-framing and speaker detection
- [Calendar Integration](/docs/calendar/) - Show meetings on screen
- [Fleet Management](/docs/management/) - Centralized UI configuration
