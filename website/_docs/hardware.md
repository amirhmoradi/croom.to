---
title: Hardware Guide
description: Recommended hardware and compatibility for Croom devices.
order: 3
---

# Hardware Guide

Croom is designed to run on affordable, readily available hardware. This guide covers recommended configurations and compatibility.

## Recommended Configurations

### Basic Setup (~$150)

Best for small huddle rooms and personal offices.

| Component | Recommendation | Price |
|-----------|---------------|-------|
| Computer | Raspberry Pi 4 (4GB) | ~$55 |
| Camera | Logitech C920/C922 | ~$70 |
| Storage | 32GB MicroSD | ~$10 |
| Power | Official Pi 4 PSU | ~$10 |
| Case | Official Pi 4 Case | ~$5 |

### Standard Setup (~$350)

Recommended for most meeting rooms.

| Component | Recommendation | Price |
|-----------|---------------|-------|
| Computer | Raspberry Pi 5 (8GB) | ~$80 |
| Camera | Logitech C930e or similar | ~$100 |
| AI Accelerator | Hailo-8L M.2 HAT | ~$70 |
| Storage | 64GB MicroSD | ~$15 |
| Touch Screen | 7" Official Display | ~$70 |
| Power | Official Pi 5 PSU | ~$12 |

### Premium Setup (~$600)

For large conference rooms with PTZ cameras.

| Component | Recommendation | Price |
|-----------|---------------|-------|
| Computer | Raspberry Pi 5 (8GB) | ~$80 |
| Camera | PTZ Optics or similar | ~$300 |
| AI Accelerator | Hailo-8L M.2 HAT | ~$70 |
| Storage | 128GB MicroSD | ~$20 |
| Touch Screen | 10" IPS Display | ~$100 |
| Speakerphone | Jabra Speak 510 | ~$100 |

## Supported Hardware

### Single Board Computers

| Device | Status | Notes |
|--------|--------|-------|
| Raspberry Pi 5 | ✅ Recommended | Best performance, native M.2 support |
| Raspberry Pi 4 | ✅ Supported | Good performance, widely available |
| Raspberry Pi 400 | ✅ Supported | Built-in keyboard, great for demos |
| Orange Pi 5 | 🔶 Experimental | Community-supported |
| x86_64 Linux | ✅ Supported | Intel NUC, mini PCs |

### Cameras

#### USB Webcams

| Camera | Status | Notes |
|--------|--------|-------|
| Logitech C920/C922/C930e | ✅ Excellent | Best overall compatibility |
| Logitech BRIO | ✅ Excellent | 4K support |
| Razer Kiyo | ✅ Good | Built-in ring light |
| Microsoft LifeCam | ✅ Good | Budget option |
| Generic UVC cameras | ✅ Good | Most USB cameras work |

#### PTZ Cameras

| Camera | Status | Notes |
|--------|--------|-------|
| PTZ Optics (various) | ✅ Supported | VISCA/ONVIF control |
| Logitech Rally | 🔶 Partial | USB only, no PTZ control |
| AVer PTZ series | ✅ Supported | VISCA control |
| HuddleCam | ✅ Supported | VISCA/ONVIF control |

### AI Accelerators

| Accelerator | Performance | Notes |
|-------------|------------|-------|
| Hailo-8L | 26 TOPS | Recommended for Pi 5 |
| Hailo-8 | 26 TOPS | Higher power, needs cooling |
| Coral USB | 4 TOPS | Easy USB connection |
| Coral M.2 | 4 TOPS | Faster than USB version |
| CPU only | N/A | Works without accelerator |

### Audio Devices

| Device | Status | Notes |
|--------|--------|-------|
| USB speakerphones | ✅ Recommended | Jabra, Poly, Anker |
| USB microphones | ✅ Supported | Blue Yeti, etc. |
| 3.5mm audio | ✅ Supported | Via Pi audio jack |
| HDMI audio | ✅ Supported | Pass-through to display |
| Bluetooth | 🔶 Experimental | May have latency |

### Displays

| Display | Status | Notes |
|---------|--------|-------|
| Any HDMI display | ✅ Supported | TVs, monitors, projectors |
| Official Pi Display | ✅ Recommended | Touch support built-in |
| Third-party DSI | ✅ Supported | Various sizes available |
| USB touchscreens | ✅ Supported | May need driver config |

## HDMI-CEC Compatibility

HDMI-CEC allows Croom to control your display automatically. Compatibility varies by manufacturer:

| Brand | Status | Notes |
|-------|--------|-------|
| Samsung | ✅ Good | Called "Anynet+" |
| LG | ✅ Good | Called "SimpLink" |
| Sony | ✅ Good | Called "BRAVIA Sync" |
| Philips | ✅ Good | Called "EasyLink" |
| Vizio | 🔶 Partial | Some models limited |
| TCL/Roku | 🔶 Partial | Basic functions only |

## Power Requirements

| Device | Minimum | Recommended |
|--------|---------|-------------|
| Pi 4 | 5V 2.5A | 5V 3A |
| Pi 5 | 5V 3A | 5V 5A (27W PD) |
| With Hailo HAT | +5W | Use official PSU |
| With USB devices | +5W per device | Consider powered hub |

## Cooling

Active cooling is recommended for:

- Raspberry Pi 5 (always)
- Raspberry Pi 4 with AI accelerator
- Any device in warm environments (>25°C)

Recommended cooling solutions:

- Official Active Cooler for Pi 5
- Pimoroni Fan Shim for Pi 4
- Argon ONE case with fan
- Custom 3D printed cases with fans

## Next Steps

- [Installation Guide](/docs/installation/) - Set up your hardware
- [Configuration](/docs/configuration/) - Configure your device
- [AI Features](/docs/ai-features/) - Enable AI accelerator features
