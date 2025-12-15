# PiMeet Administrator Guide

## Overview

This guide is for IT administrators responsible for deploying, configuring, and maintaining PiMeet devices across an organization.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Architecture Overview](#2-architecture-overview)
3. [Initial Setup](#3-initial-setup)
4. [Device Management](#4-device-management)
5. [Configuration](#5-configuration)
6. [Monitoring & Alerting](#6-monitoring--alerting)
7. [Security](#7-security)
8. [Troubleshooting](#8-troubleshooting)
9. [Maintenance](#9-maintenance)
10. [Best Practices](#10-best-practices)

---

## 1. System Requirements

### 1.1 Hardware Requirements

#### PiMeet Device
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Device | Raspberry Pi 4B 2GB | Raspberry Pi 4B 4GB |
| Storage | 16GB microSD | 32GB microSD (Class 10) |
| Power | Official 5V 3A USB-C | Official 5V 3A USB-C |
| Cooling | Passive heatsink | ArgonOne case (active) |

#### Peripherals
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Camera | Any USB webcam | Logitech C920/C922 |
| Audio | Webcam mic + TV speakers | Jabra Speak 510 |
| TV | Any HDMI TV | HDMI-CEC compatible |

### 1.2 Network Requirements

| Requirement | Details |
|-------------|---------|
| Connectivity | WiFi (WPA2/WPA3) or Ethernet |
| Bandwidth | 2 Mbps per device (minimum) |
| Latency | <100ms to meeting servers |
| Ports | HTTPS (443), WebRTC media ports |

#### Firewall Rules (Outbound)
```
# Required
TCP 443  → *.google.com, *.microsoft.com, *.zoom.us
UDP 3478 → STUN/TURN servers
UDP 10000-20000 → Media (varies by platform)

# Management Dashboard
TCP 443  → dashboard.yourcompany.com
```

### 1.3 Software Requirements

#### Management Dashboard Server
| Component | Requirement |
|-----------|-------------|
| OS | Ubuntu 20.04+, RHEL 8+, or Docker |
| CPU | 2+ cores |
| RAM | 4GB minimum, 8GB recommended |
| Storage | 50GB+ (depends on retention) |
| Database | PostgreSQL 13+ |

---

## 2. Architecture Overview

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cloud/On-Premise                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Management  │  │   Database  │  │   Message   │              │
│  │  Dashboard  │  │ (PostgreSQL)│  │    Queue    │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                     │
│         └────────────────┴────────────────┘                     │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │ HTTPS/WSS
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
         ┌─────────┐  ┌─────────┐  ┌─────────┐
         │ PiMeet  │  │ PiMeet  │  │ PiMeet  │
         │ Device 1│  │ Device 2│  │ Device N│
         └─────────┘  └─────────┘  └─────────┘
```

### 2.2 Device Software Stack

```
┌─────────────────────────────────────────┐
│           Meeting Platform              │
│  (Google Meet/Teams/Zoom/Webex)        │
├─────────────────────────────────────────┤
│         Chromium Browser                │
│  (Hardware accelerated, extensions)    │
├─────────────────────────────────────────┤
│         PiMeet Agent                    │
│  (Device management, metrics, config)  │
├─────────────────────────────────────────┤
│         System Services                 │
│  (systemd, NetworkManager, PulseAudio) │
├─────────────────────────────────────────┤
│      Raspberry Pi OS (64-bit)          │
├─────────────────────────────────────────┤
│         Raspberry Pi 4B                 │
└─────────────────────────────────────────┘
```

---

## 3. Initial Setup

### 3.1 Image Preparation

#### Option A: Pre-built Image
Download the latest PiMeet image from releases:
```bash
wget https://github.com/your-org/pimeet/releases/latest/pimeet.img.gz
gunzip pimeet.img.gz
```

#### Option B: Build from Source
```bash
git clone https://github.com/your-org/pimeet.git
cd pimeet/build
./download-img.sh
./prep-img.sh
```

### 3.2 Flashing SD Cards

#### Single Device
```bash
# Identify SD card device
lsblk

# Flash image (replace /dev/sdX with your device)
sudo dd if=pimeet.img of=/dev/sdX bs=4M status=progress
sync
```

#### Bulk Flashing
Use tools like Balena Etcher for multiple cards, or:
```bash
# Flash multiple cards in parallel
for dev in /dev/sd{b,c,d}; do
  sudo dd if=pimeet.img of=$dev bs=4M &
done
wait
```

### 3.3 First Boot Configuration

#### Method 1: Captive Portal (Recommended)
1. Insert SD card and power on device
2. Connect to `PiMeet-Setup-XXXX` WiFi
3. Browser opens setup wizard automatically
4. Configure WiFi, credentials, and room name
5. Device reboots and registers with dashboard

#### Method 2: USB Configuration
Create `pimeet-config.yaml` on USB drive:
```yaml
version: 1
device:
  name: "Conference Room A"
  location: "Building 1, Floor 2"
  timezone: "America/Los_Angeles"

network:
  wifi:
    ssid: "CorpWiFi"
    password: "your-wifi-password"

meeting:
  platform: "google_meet"
  credentials:
    email: "room-a@company.com"
    password: "meeting-account-password"

dashboard:
  url: "https://pimeet.yourcompany.com"
  enrollment_token: "your-enrollment-token"
```

Insert USB before booting, device auto-configures.

#### Method 3: Dashboard Pre-registration
1. Add device to dashboard with MAC address
2. Generate enrollment token
3. Boot device on network
4. Device contacts dashboard and receives config

### 3.4 Dashboard Installation

#### Docker (Recommended)
```bash
# Pull and run
docker-compose -f docker-compose.prod.yml up -d

# Initial setup
docker exec -it pimeet-dashboard ./manage.py createsuperuser
```

#### Manual Installation
```bash
# Clone repository
git clone https://github.com/your-org/pimeet-dashboard.git
cd pimeet-dashboard

# Install dependencies
npm install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Initialize database
./manage.py migrate
./manage.py createsuperuser

# Start services
./manage.py runserver
```

---

## 4. Device Management

### 4.1 Dashboard Overview

#### Device List View
- Status indicators (online/offline/in-meeting)
- Last seen timestamp
- Meeting platform and account
- Location and tags
- Quick actions

#### Device Detail View
- Real-time metrics (CPU, memory, temperature)
- Current status and meeting info
- Configuration panel
- Logs and history
- Remote actions

### 4.2 Device Operations

#### Remote Restart
```bash
# Via dashboard
Dashboard → Devices → [Device] → Actions → Restart

# Via API
curl -X POST https://dashboard/api/v1/devices/{id}/actions \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"action": "restart"}'
```

#### Configuration Update
```bash
# Via dashboard
Dashboard → Devices → [Device] → Configuration → Edit

# Via API
curl -X PUT https://dashboard/api/v1/devices/{id}/config \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"meeting": {"platform": "teams"}}'
```

#### Software Update
```bash
# Via dashboard (bulk)
Dashboard → Devices → Select All → Actions → Update Software

# Automatic updates
Configure auto-update policy in Dashboard → Settings → Updates
```

### 4.3 Grouping & Organization

#### Device Groups
Organize devices by:
- Location (building, floor, region)
- Department
- Platform preference
- Custom tags

#### Bulk Operations
- Select multiple devices
- Apply configuration template
- Push updates
- Export reports

---

## 5. Configuration

### 5.1 Device Configuration

#### Core Settings
| Setting | Description | Default |
|---------|-------------|---------|
| `device.name` | Display name | Hostname |
| `device.location` | Physical location | - |
| `device.timezone` | Time zone | UTC |
| `device.auto_update` | Enable auto-updates | true |

#### Meeting Settings
| Setting | Description | Default |
|---------|-------------|---------|
| `meeting.platform` | Primary platform | google_meet |
| `meeting.join_early` | Minutes before meeting | 1 |
| `meeting.auto_leave` | Leave when empty | true |
| `meeting.camera_default` | Camera on by default | true |
| `meeting.mic_default` | Mic on by default | true |

#### Network Settings
| Setting | Description | Default |
|---------|-------------|---------|
| `network.wifi.ssid` | WiFi network name | - |
| `network.proxy` | HTTP proxy URL | - |
| `network.ntp_server` | NTP server | pool.ntp.org |

### 5.2 Configuration Templates

Create reusable templates for consistent deployment:

```yaml
# template-standard-room.yaml
name: "Standard Conference Room"
settings:
  meeting:
    platform: auto
    join_early: 2
    auto_leave: true
  audio:
    device: auto
    echo_cancellation: true
  video:
    device: auto
    resolution: 1080p
```

Apply templates:
```bash
# Dashboard
Dashboard → Configuration → Templates → Apply to Devices

# API
curl -X POST https://dashboard/api/v1/devices/bulk/config \
  -d '{"device_ids": ["id1", "id2"], "template": "standard-room"}'
```

### 5.3 Calendar Configuration

#### Google Calendar
1. Create service account in Google Cloud Console
2. Enable Calendar API
3. Share room calendars with service account
4. Configure in dashboard with service account credentials

#### Microsoft 365
1. Register application in Azure AD
2. Configure Calendar.Read permissions
3. Grant admin consent
4. Configure in dashboard with app credentials

---

## 6. Monitoring & Alerting

### 6.1 Metrics Collected

#### System Metrics
| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| CPU Usage | CPU utilization % | >90% for 5 min |
| Memory Usage | RAM utilization % | >90% for 5 min |
| Temperature | CPU temperature °C | >70°C |
| Disk Usage | Storage utilization % | >90% |
| Network Latency | Ping to dashboard ms | >500ms |

#### Meeting Metrics
| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Join Success | Meeting join success rate | <95% |
| Join Time | Seconds to join meeting | >60s |
| Audio Quality | Audio bitrate/quality | Below threshold |
| Video Quality | Video resolution/fps | Below threshold |

### 6.2 Alert Configuration

#### Alert Rules
```yaml
# alerts.yaml
rules:
  - name: device_offline
    condition: "status == 'offline' for 5m"
    severity: critical
    channels: [email, slack]

  - name: high_temperature
    condition: "temperature > 70"
    severity: warning
    channels: [email]

  - name: meeting_join_failed
    condition: "join_failures > 3 in 1h"
    severity: critical
    channels: [email, slack, pagerduty]
```

#### Alert Channels
| Channel | Configuration |
|---------|---------------|
| Email | SMTP server, recipients |
| Slack | Webhook URL, channel |
| PagerDuty | Integration key |
| Webhook | Custom URL endpoint |

### 6.3 Dashboards & Reports

#### Built-in Dashboards
- Fleet overview (all devices status)
- Meeting analytics (usage, quality)
- System health (resource utilization)
- Alerts dashboard (active, history)

#### Custom Reports
```bash
# Generate usage report
Dashboard → Reports → New Report → Usage Report

# Schedule weekly reports
Dashboard → Reports → Schedule → Weekly → Email to admins
```

---

## 7. Security

### 7.1 Access Control

#### User Roles
| Role | Permissions |
|------|-------------|
| Super Admin | Full access, user management |
| IT Admin | Device management, configuration |
| Site Admin | Manage assigned locations only |
| Viewer | Read-only access |

#### Creating Users
```bash
# Dashboard
Dashboard → Settings → Users → Add User

# CLI
./manage.py createuser --email admin@company.com --role it_admin
```

### 7.2 Authentication

#### Local Authentication
- Password requirements: 12+ chars, complexity
- Account lockout after 5 failed attempts
- Password expiration: 90 days (configurable)

#### SSO Configuration (SAML)
```yaml
# saml.yaml
idp:
  entity_id: "https://idp.company.com"
  sso_url: "https://idp.company.com/sso"
  certificate: |
    -----BEGIN CERTIFICATE-----
    ...
    -----END CERTIFICATE-----
sp:
  entity_id: "https://pimeet.company.com"
  acs_url: "https://pimeet.company.com/auth/saml/acs"
```

### 7.3 Credential Security

#### Encryption
- All credentials encrypted with AES-256-GCM
- Per-device encryption keys
- Master key stored in environment/vault

#### Secret Manager Integration
```yaml
# config.yaml
secrets:
  provider: hashicorp_vault
  vault_addr: "https://vault.company.com"
  vault_path: "secret/pimeet"
  auth_method: kubernetes  # or approle, token
```

### 7.4 Audit Logging

#### Logged Events
- All authentication attempts
- Configuration changes
- Credential access
- Device operations
- User management actions

#### Log Export
```bash
# Export to SIEM
Dashboard → Settings → Integrations → SIEM → Configure

# Manual export
curl https://dashboard/api/v1/audit-logs \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"start": "2025-01-01", "end": "2025-01-31"}' \
  > audit-logs.json
```

---

## 8. Troubleshooting

### 8.1 Common Issues

#### Device Not Coming Online

| Symptom | Check | Solution |
|---------|-------|----------|
| No network | WiFi credentials | Re-run setup wizard |
| Can't reach dashboard | Firewall rules | Open TCP 443 outbound |
| Certificate error | System time | Sync NTP |
| Agent not running | Service status | Restart pimeet-agent |

```bash
# SSH to device and check
ssh pi@device-ip

# Check network
ping -c 3 8.8.8.8
ping -c 3 dashboard.company.com

# Check agent status
sudo systemctl status pimeet-agent

# Check logs
sudo journalctl -u pimeet-agent -f
```

#### Meeting Join Failures

| Symptom | Check | Solution |
|---------|-------|----------|
| Authentication error | Credentials | Update credentials |
| Platform blocked | Browser | Clear cache, update |
| No calendar events | Calendar sync | Check calendar permissions |
| Timeout | Network | Check bandwidth |

```bash
# Check Chromium logs
cat ~/.config/chromium/chrome_debug.log

# Test meeting manually
chromium-browser --temp-profile "https://meet.google.com/test-meeting"
```

#### Audio/Video Issues

| Symptom | Check | Solution |
|---------|-------|----------|
| No audio | Device selection | Check pulseaudio settings |
| No video | Webcam connected | Check lsusb, permissions |
| Poor quality | Bandwidth | Check network speed |
| Echo | Settings | Enable echo cancellation |

```bash
# List audio devices
pactl list short sinks
pactl list short sources

# List video devices
v4l2-ctl --list-devices

# Test webcam
ffplay /dev/video0
```

### 8.2 Remote Diagnostics

#### Via Dashboard
- View device logs in real-time
- Screenshot current display
- Run network diagnostics
- Check system metrics

#### Via SSH
Enable emergency SSH access:
```bash
# Dashboard
Dashboard → Devices → [Device] → Emergency Access → Enable SSH

# SSH in (uses certificate authentication)
ssh -i emergency.key admin@device-ip
```

### 8.3 Recovery Procedures

#### Factory Reset
```bash
# Via physical access
# Hold button for 10 seconds during boot

# Via dashboard
Dashboard → Devices → [Device] → Actions → Factory Reset
```

#### Reflashing Device
1. Remove SD card from device
2. Flash new image
3. Device re-provisions on boot

---

## 9. Maintenance

### 9.1 Regular Tasks

#### Daily
- Check for offline devices
- Review critical alerts
- Monitor meeting success rate

#### Weekly
- Review device health reports
- Check for available updates
- Review audit logs

#### Monthly
- Apply software updates
- Review user access
- Test backup/recovery
- Review capacity

#### Quarterly
- Security review
- Performance optimization
- Documentation updates
- Disaster recovery test

### 9.2 Updates

#### Device Updates
```bash
# Automatic (recommended)
Dashboard → Settings → Updates → Enable Auto-Update

# Manual (scheduled)
Dashboard → Devices → Select → Actions → Schedule Update

# Emergency (immediate)
Dashboard → Devices → Select → Actions → Update Now
```

#### Dashboard Updates
```bash
# Docker
docker-compose pull
docker-compose up -d

# Manual
git pull
npm install
pip install -r requirements.txt
./manage.py migrate
systemctl restart pimeet-dashboard
```

### 9.3 Backup & Recovery

#### Dashboard Backup
```bash
# Database backup
pg_dump pimeet > backup-$(date +%Y%m%d).sql

# Full backup (database + config)
./scripts/backup.sh /backup/location
```

#### Device Backup
```bash
# Export device configurations
Dashboard → Devices → Export → All Configurations
```

#### Recovery
```bash
# Restore database
psql pimeet < backup-20250115.sql

# Restore device config
Dashboard → Devices → Import → Upload backup file
```

---

## 10. Best Practices

### 10.1 Deployment

- Use consistent hardware across all rooms
- Pre-register devices in dashboard before deployment
- Use configuration templates for consistency
- Document room-specific requirements
- Label devices and cables clearly

### 10.2 Security

- Enable MFA for all admin accounts
- Use SSO when available
- Rotate credentials quarterly
- Review audit logs regularly
- Keep software updated

### 10.3 Monitoring

- Set up alerts for critical metrics
- Create dashboards for each location
- Review weekly health reports
- Track meeting success rates
- Monitor bandwidth usage

### 10.4 Documentation

- Maintain room inventory spreadsheet
- Document network configurations
- Keep runbooks updated
- Train help desk staff
- Create user quick-reference cards

---

## Appendix

### A. CLI Reference

```bash
# Agent CLI
pimeet-cli status          # Show device status
pimeet-cli config show     # Show current config
pimeet-cli config set      # Update config
pimeet-cli logs            # View logs
pimeet-cli restart         # Restart agent
pimeet-cli update          # Check for updates
```

### B. API Reference

See [API Documentation](../api-reference.md) for complete API reference.

### C. Glossary

| Term | Definition |
|------|------------|
| Agent | Software running on PiMeet device |
| Dashboard | Web-based management interface |
| Platform | Meeting service (Meet, Teams, Zoom) |
| Provisioning | Initial device setup process |
| Template | Reusable configuration preset |

---

## Version Information

| Document | Version |
|----------|---------|
| Administrator Guide | 1.0 |
| Last Updated | 2025-12-15 |
