---
title: Installation
description: Detailed installation instructions for Croom on various platforms.
order: 4
---

# Installation Guide

This guide covers installation methods for different platforms and use cases.

## Installation Methods

### Method 1: Pre-built Image (Recommended)

The easiest way to get started. Download our pre-built image with everything configured.

```bash
# For Raspberry Pi 5
wget https://releases.croom.to/latest/croom-rpi5.img.gz
gunzip -c croom-rpi5.img.gz | sudo dd of=/dev/sdX bs=4M status=progress

# For Raspberry Pi 4
wget https://releases.croom.to/latest/croom-rpi4.img.gz
gunzip -c croom-rpi4.img.gz | sudo dd of=/dev/sdX bs=4M status=progress
```

### Method 2: Install Script

Install on an existing Raspberry Pi OS installation:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Download and run installer
curl -fsSL https://get.croom.to | sudo bash
```

The installer will:
1. Install all dependencies
2. Configure the system
3. Set up the Croom service
4. Start the setup wizard

### Method 3: Manual Installation

For advanced users who want full control:

```bash
# Install system dependencies
sudo apt update
sudo apt install -y \
    python3.11 python3.11-venv python3-pip \
    chromium-browser \
    libqt6-dev qt6-base-dev \
    v4l-utils \
    pulseaudio

# Clone repository
git clone https://github.com/amirhmoradi/croom.git
cd croom

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Croom
pip install -e .

# Run setup
croom setup
```

### Method 4: Docker

Run Croom in a container (best for x86_64):

```bash
# Pull the image
docker pull ghcr.io/amirhmoradi/croom:latest

# Run with device access
docker run -d \
    --name croom \
    --device /dev/video0 \
    --device /dev/snd \
    -p 8080:8080 \
    -v croom-data:/data \
    ghcr.io/amirhmoradi/croom:latest
```

## Platform-Specific Instructions

### Raspberry Pi 5

The Pi 5 is our recommended platform with best performance.

```bash
# Enable PCIe for Hailo HAT (if using)
sudo raspi-config nonint do_pcie_ext 1

# Configure boot settings
sudo nano /boot/firmware/config.txt
```

Add these lines:
```
# Enable PCIe Gen 3 for Hailo
dtparam=pciex1_gen=3

# GPU memory (required for video)
gpu_mem=256

# Enable camera
start_x=1
```

### Raspberry Pi 4

```bash
# Configure boot settings
sudo nano /boot/config.txt
```

Add these lines:
```
# GPU memory
gpu_mem=256

# Enable camera
start_x=1

# Increase USB current (if needed)
max_usb_current=1
```

### x86_64 Linux (Ubuntu/Debian)

```bash
# Install dependencies
sudo apt update
sudo apt install -y \
    python3.11 python3.11-venv \
    chromium-browser \
    qt6-base-dev libqt6multimedia6 \
    pulseaudio pavucontrol

# Continue with install script
curl -fsSL https://get.croom.to | sudo bash
```

## Post-Installation

### Verify Installation

```bash
# Check Croom service status
sudo systemctl status croom

# Check logs
sudo journalctl -u croom -f

# Test camera
v4l2-ctl --list-devices

# Test audio
aplay -l
arecord -l
```

### Enable Auto-Start

Croom starts automatically by default. To manage:

```bash
# Enable auto-start
sudo systemctl enable croom

# Disable auto-start
sudo systemctl disable croom

# Start manually
sudo systemctl start croom

# Stop
sudo systemctl stop croom
```

### Configure Firewall

If using a firewall, allow these ports:

```bash
# Web interface
sudo ufw allow 8080/tcp

# Fleet management API
sudo ufw allow 8443/tcp

# mDNS (for discovery)
sudo ufw allow 5353/udp
```

## Upgrading

### From Pre-built Image

Download and flash the new image, then restore your configuration:

```bash
# Backup configuration first
scp pi@croom:/etc/croom/config.yaml ./backup/
```

### From Install Script

```bash
# Update Croom
sudo croom update

# Or manually
cd /opt/croom
git pull
pip install -e .
sudo systemctl restart croom
```

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop croom
sudo systemctl disable croom

# Remove files
sudo rm -rf /opt/croom
sudo rm /etc/systemd/system/croom.service

# Remove configuration (optional)
sudo rm -rf /etc/croom
```

## Troubleshooting Installation

### Python version issues

```bash
# Check Python version
python3 --version

# Install Python 3.11 if needed
sudo apt install python3.11 python3.11-venv
```

### Permission errors

```bash
# Add user to required groups
sudo usermod -aG video,audio,gpio,i2c $USER

# Reboot to apply
sudo reboot
```

### Camera not detected

```bash
# Check if camera is connected
lsusb | grep -i cam

# Check video devices
ls -la /dev/video*

# Load v4l2 module
sudo modprobe bcm2835-v4l2
```

## Next Steps

- [Configuration](/docs/configuration/) - Configure your installation
- [Quick Start](/docs/quickstart/) - Complete initial setup
- [Hardware Guide](/docs/hardware/) - Optimize hardware settings
