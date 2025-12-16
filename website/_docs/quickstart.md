---
title: Quick Start
description: Get your first Croom device up and running in 15 minutes.
order: 2
---

# Quick Start Guide

This guide will help you set up your first Croom video conferencing device in about 15 minutes.

## Prerequisites

Before you begin, make sure you have:

- **Raspberry Pi 4 or 5** (4GB+ RAM recommended)
- **MicroSD card** (32GB+ recommended)
- **USB webcam** or compatible camera
- **HDMI display** (TV or monitor)
- **USB keyboard/mouse** (for initial setup)
- **Ethernet cable** or WiFi connection

## Step 1: Flash the Image

Download the latest Croom image and flash it to your SD card:

```bash
# Download the image
wget https://releases.croom.to/latest/croom-rpi5.img.gz

# Flash to SD card (replace /dev/sdX with your device)
gunzip -c croom-rpi5.img.gz | sudo dd of=/dev/sdX bs=4M status=progress
```

Or use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) with our custom image.

## Step 2: First Boot

1. Insert the SD card into your Raspberry Pi
2. Connect your camera, display, and network
3. Power on the device
4. Wait for the setup wizard to appear (2-3 minutes)

## Step 3: Initial Configuration

The setup wizard will guide you through:

1. **Network Setup** - Connect to WiFi or verify Ethernet
2. **Time Zone** - Set your local time zone
3. **Room Name** - Give your room a friendly name
4. **Calendar** - Optionally connect Google or Microsoft calendar
5. **Test Call** - Verify camera and audio work

## Step 4: Join Your First Meeting

Once setup is complete, you can join meetings in several ways:

### From the Touch Screen

1. Tap "Join Meeting"
2. Enter the meeting URL or code
3. Select the platform (Google Meet, Zoom, Teams, Webex)
4. Tap "Join"

### From Calendar

If you connected a calendar, upcoming meetings appear automatically:

1. Tap on a scheduled meeting
2. Tap "Join Now"

### Via QR Code

Scan this QR code on your phone to control the room:

1. Point your phone's camera at the QR code
2. Open the link
3. Control the room from your phone

## Next Steps

Now that your device is running, explore these features:

- [Configure AI features](/docs/ai-features/) - Enable auto-framing and speaker detection
- [Set up calendar sync](/docs/calendar/) - Automatic meeting joins
- [Customize the touch screen](/docs/touch-screen/) - Branding and layouts
- [Connect to fleet management](/docs/management/) - Centralized control

## Troubleshooting

### Device doesn't boot

- Ensure the SD card is properly inserted
- Try re-flashing the image
- Check power supply (5V 3A for Pi 4, 5V 5A for Pi 5)

### No video/audio

- Check camera permissions in browser
- Verify camera is detected: `v4l2-ctl --list-devices`
- Check audio devices: `aplay -l`

### Can't connect to network

- Verify Ethernet cable is connected
- For WiFi, ensure credentials are correct
- Check router DHCP settings

### Need more help?

- [Full troubleshooting guide](/docs/troubleshooting/)
- [GitHub Issues](https://github.com/amirhmoradi/croom/issues)
- [Community Discussions](https://github.com/amirhmoradi/croom/discussions)
