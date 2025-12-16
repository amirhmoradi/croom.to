---
title: Fleet Management
description: Centralized management and monitoring for Croom devices.
order: 8
---

# Fleet Management

Manage hundreds of Croom devices from a single dashboard.

## Overview

The Fleet Management Dashboard provides:

- Real-time device status monitoring
- Centralized configuration management
- Remote troubleshooting
- OTA updates
- Analytics and reporting
- Alert notifications

## Getting Started

### Self-Hosted Setup

Deploy your own fleet management server:

```bash
# Clone the management server
git clone https://github.com/amirhmoradi/croom-management.git
cd croom-management

# Configure
cp .env.example .env
nano .env

# Start with Docker
docker-compose up -d
```

Required environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/croom

# Authentication
JWT_SECRET=your-secure-secret
ADMIN_EMAIL=admin@company.com

# Server
HOST=0.0.0.0
PORT=8443
SSL_CERT=/path/to/cert.pem
SSL_KEY=/path/to/key.pem
```

### Connecting Devices

On each Croom device:

```yaml
# /etc/croom/config.yaml
management:
  enabled: true
  server: "https://fleet.company.com:8443"
  api_key: "device-specific-api-key"

  # Sync interval
  sync_interval: 60  # Seconds

  # Features
  remote_access: true
  ota_updates: true
  log_upload: true
```

Or use environment variables:

```bash
export CROOM_MANAGEMENT_SERVER="https://fleet.company.com:8443"
export CROOM_MANAGEMENT_API_KEY="your-api-key"
```

## Dashboard Features

### Device Overview

View all devices at a glance:

- **Status**: Online, offline, in-meeting, idle
- **Health**: CPU, memory, temperature
- **Version**: Current software version
- **Last seen**: Connection status

### Device Groups

Organize devices by:

- Location (building, floor, region)
- Department
- Device type
- Custom tags

```yaml
# Group configuration
groups:
  - name: "Building A"
    filter:
      location: "building-a"
    config:
      timezone: "America/New_York"

  - name: "Executive Rooms"
    filter:
      tags: ["executive"]
    config:
      touch_screen:
        theme: "dark"
        branding:
          logo: "exec-logo.png"
```

### Remote Configuration

Push configuration changes to devices:

```yaml
# Configuration policy
policy:
  name: "Standard Meeting Room"
  priority: 100

  # Target devices
  target:
    groups: ["all-rooms"]
    exclude_tags: ["special-config"]

  # Configuration
  config:
    display:
      hdmi_cec: true
      standby_timeout: 300

    ai:
      auto_framing: true
      noise_reduction: true

    platforms:
      google_meet:
        enabled: true
      zoom:
        enabled: true
```

### Remote Actions

Execute actions on devices:

- **Reboot**: Restart the device
- **Update**: Push software updates
- **Join Meeting**: Force join a meeting URL
- **Leave Meeting**: End current meeting
- **Screenshot**: Capture current display
- **Logs**: Download device logs

## Monitoring & Alerts

### Health Metrics

Monitor device health in real-time:

```yaml
monitoring:
  metrics:
    - cpu_usage
    - memory_usage
    - disk_usage
    - temperature
    - network_latency
    - meeting_quality

  # Collection interval
  interval: 30  # Seconds

  # Retention
  retention: 30  # Days
```

### Alert Rules

Configure alerts for issues:

```yaml
alerts:
  - name: "Device Offline"
    condition: "status == 'offline'"
    duration: "5m"
    severity: "critical"
    notify:
      - email: "it@company.com"
      - slack: "#room-alerts"

  - name: "High Temperature"
    condition: "temperature > 80"
    duration: "2m"
    severity: "warning"
    notify:
      - email: "it@company.com"

  - name: "Low Disk Space"
    condition: "disk_usage > 90"
    severity: "warning"
    notify:
      - email: "it@company.com"
```

### Notification Channels

```yaml
notifications:
  email:
    smtp_host: "smtp.company.com"
    smtp_port: 587
    from: "croom-alerts@company.com"

  slack:
    webhook_url: "https://hooks.slack.com/..."

  teams:
    webhook_url: "https://outlook.office.com/webhook/..."

  pagerduty:
    integration_key: "your-key"
```

## OTA Updates

### Update Management

```yaml
updates:
  # Automatic updates
  auto_update: true

  # Update window
  window:
    start: "02:00"
    end: "05:00"
    days: ["sunday", "wednesday"]

  # Staged rollout
  rollout:
    enabled: true
    stages:
      - name: "Canary"
        percent: 5
        duration: "24h"
      - name: "Early Adopters"
        percent: 25
        duration: "48h"
      - name: "General"
        percent: 100
```

### Manual Updates

Push updates to specific devices or groups:

```bash
# CLI
croom-manage update push --version 1.5.0 --group "building-a"

# API
curl -X POST https://fleet.company.com/api/v1/updates \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"version": "1.5.0", "group": "building-a"}'
```

## Analytics & Reporting

### Usage Metrics

Track room utilization:

- Meetings per day/week/month
- Average meeting duration
- Peak usage hours
- No-show rates
- Platform breakdown

### Reports

Generate automated reports:

```yaml
reports:
  - name: "Weekly Summary"
    schedule: "0 8 * * 1"  # Monday 8am
    include:
      - device_status
      - meeting_stats
      - issues
    format: "pdf"
    recipients:
      - "it@company.com"
      - "facilities@company.com"

  - name: "Monthly Analytics"
    schedule: "0 8 1 * *"  # 1st of month
    include:
      - utilization
      - trends
      - recommendations
    format: "pdf"
    recipients:
      - "management@company.com"
```

## API Reference

### Authentication

```bash
# Get API token
curl -X POST https://fleet.company.com/api/v1/auth/token \
  -d '{"email": "admin@company.com", "password": "..."}'

# Use token
curl -H "Authorization: Bearer $TOKEN" \
  https://fleet.company.com/api/v1/devices
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/devices` | List all devices |
| GET | `/api/v1/devices/:id` | Get device details |
| PATCH | `/api/v1/devices/:id` | Update device config |
| POST | `/api/v1/devices/:id/reboot` | Reboot device |
| GET | `/api/v1/groups` | List device groups |
| POST | `/api/v1/updates` | Push update |
| GET | `/api/v1/analytics` | Get analytics data |

### Webhooks

Receive events via webhooks:

```yaml
webhooks:
  - url: "https://company.com/croom-webhook"
    events:
      - "device.online"
      - "device.offline"
      - "meeting.started"
      - "meeting.ended"
      - "alert.triggered"
    secret: "webhook-secret"
```

## Security

### Access Control

```yaml
security:
  # Role-based access
  roles:
    admin:
      permissions: ["*"]

    operator:
      permissions:
        - "devices.read"
        - "devices.reboot"
        - "meetings.join"

    viewer:
      permissions:
        - "devices.read"
        - "analytics.read"

  # SSO integration
  sso:
    enabled: true
    provider: "azure-ad"
    tenant_id: "your-tenant"
    client_id: "your-client-id"
```

### Audit Logging

All actions are logged:

```yaml
audit:
  enabled: true
  retention: 365  # Days

  # Log destinations
  destinations:
    - type: "database"
    - type: "syslog"
      server: "syslog.company.com:514"
```

## Troubleshooting

### Device not connecting

1. Check network connectivity
2. Verify API key is correct
3. Check firewall allows outbound HTTPS
4. View device logs:
   ```bash
   sudo journalctl -u croom | grep management
   ```

### Configuration not syncing

1. Check sync interval settings
2. Verify device is online in dashboard
3. Check for configuration errors:
   ```bash
   croom config validate
   ```

### Updates failing

1. Check device disk space
2. Verify update server is reachable
3. Check update logs:
   ```bash
   cat /var/log/croom/update.log
   ```

## Next Steps

- [Provisioning](/docs/provisioning/) - Zero-touch deployment
- [API Reference](/docs/api/) - Full API documentation
- [Security](/docs/security/) - Security best practices
