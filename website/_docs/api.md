---
title: API Reference
description: REST API documentation for Croom device and fleet management.
order: 9
---

# API Reference

Croom provides REST APIs for device control and fleet management.

## Device API

Each Croom device runs a local API server for direct control.

### Base URL

```
http://croom-device.local:8080/api/v1
```

### Authentication

Local API supports multiple auth methods:

```bash
# API Key (header)
curl -H "X-API-Key: your-api-key" http://croom.local:8080/api/v1/status

# API Key (query parameter)
curl http://croom.local:8080/api/v1/status?api_key=your-api-key

# No auth (if disabled)
curl http://croom.local:8080/api/v1/status
```

### Device Status

#### Get Status

```http
GET /api/v1/status
```

Response:

```json
{
  "device": {
    "id": "croom-abc123",
    "name": "Conference Room A",
    "version": "1.5.0",
    "uptime": 86400
  },
  "meeting": {
    "active": true,
    "platform": "google_meet",
    "started_at": "2024-01-15T10:00:00Z",
    "participants": 5
  },
  "health": {
    "cpu_percent": 25,
    "memory_percent": 45,
    "temperature": 55,
    "disk_percent": 30
  }
}
```

#### Get Device Info

```http
GET /api/v1/device
```

Response:

```json
{
  "id": "croom-abc123",
  "name": "Conference Room A",
  "location": "Building 1, Floor 2",
  "hardware": {
    "model": "Raspberry Pi 5",
    "memory": "8GB",
    "storage": "64GB"
  },
  "software": {
    "version": "1.5.0",
    "os": "Raspberry Pi OS",
    "kernel": "6.1.0"
  },
  "network": {
    "hostname": "croom-room-a",
    "ip_address": "192.168.1.100",
    "mac_address": "dc:a6:32:xx:xx:xx"
  }
}
```

### Meeting Control

#### Join Meeting

```http
POST /api/v1/meeting/join
Content-Type: application/json

{
  "url": "https://meet.google.com/abc-defg-hij",
  "platform": "google_meet",
  "options": {
    "mute_audio": false,
    "disable_video": false
  }
}
```

Response:

```json
{
  "success": true,
  "meeting_id": "abc-defg-hij",
  "platform": "google_meet",
  "joined_at": "2024-01-15T10:00:00Z"
}
```

#### Leave Meeting

```http
POST /api/v1/meeting/leave
```

Response:

```json
{
  "success": true,
  "duration": 3600
}
```

#### Get Meeting Status

```http
GET /api/v1/meeting
```

Response:

```json
{
  "active": true,
  "platform": "google_meet",
  "meeting_id": "abc-defg-hij",
  "started_at": "2024-01-15T10:00:00Z",
  "duration": 1800,
  "participants": 5,
  "audio": {
    "muted": false,
    "volume": 80
  },
  "video": {
    "enabled": true,
    "resolution": "1080p"
  }
}
```

#### Control Audio

```http
POST /api/v1/meeting/audio
Content-Type: application/json

{
  "muted": true
}
```

#### Control Video

```http
POST /api/v1/meeting/video
Content-Type: application/json

{
  "enabled": false
}
```

### Camera Control

#### Get Camera Status

```http
GET /api/v1/camera
```

Response:

```json
{
  "device": "/dev/video0",
  "name": "Logitech C930e",
  "resolution": "1920x1080",
  "framerate": 30,
  "settings": {
    "brightness": 50,
    "contrast": 50,
    "auto_exposure": true
  },
  "ai": {
    "auto_framing": true,
    "speaker_detection": true,
    "current_frame": {
      "faces_detected": 3,
      "active_speaker": 1
    }
  }
}
```

#### Update Camera Settings

```http
PATCH /api/v1/camera
Content-Type: application/json

{
  "brightness": 60,
  "auto_framing": true
}
```

#### PTZ Control

```http
POST /api/v1/camera/ptz
Content-Type: application/json

{
  "action": "move",
  "pan": 10,
  "tilt": -5,
  "zoom": 0
}
```

Or use presets:

```http
POST /api/v1/camera/ptz
Content-Type: application/json

{
  "action": "preset",
  "preset": 1
}
```

### Audio Control

#### Get Audio Status

```http
GET /api/v1/audio
```

Response:

```json
{
  "input": {
    "device": "USB Audio",
    "volume": 80,
    "muted": false
  },
  "output": {
    "device": "HDMI Audio",
    "volume": 70,
    "muted": false
  },
  "processing": {
    "noise_reduction": true,
    "echo_cancellation": true
  }
}
```

#### Update Audio

```http
PATCH /api/v1/audio
Content-Type: application/json

{
  "input_volume": 85,
  "output_volume": 75,
  "noise_reduction": true
}
```

### Display Control

#### Get Display Status

```http
GET /api/v1/display
```

Response:

```json
{
  "power": "on",
  "resolution": "1920x1080",
  "hdmi_cec": {
    "enabled": true,
    "device_name": "Samsung TV"
  }
}
```

#### Control Display Power

```http
POST /api/v1/display/power
Content-Type: application/json

{
  "state": "off"
}
```

### Calendar

#### Get Upcoming Meetings

```http
GET /api/v1/calendar
```

Response:

```json
{
  "meetings": [
    {
      "id": "event123",
      "title": "Team Standup",
      "start": "2024-01-15T09:00:00Z",
      "end": "2024-01-15T09:30:00Z",
      "organizer": "alice@company.com",
      "meeting_url": "https://meet.google.com/abc-defg-hij",
      "platform": "google_meet"
    },
    {
      "id": "event456",
      "title": "Project Review",
      "start": "2024-01-15T14:00:00Z",
      "end": "2024-01-15T15:00:00Z",
      "organizer": "bob@company.com",
      "meeting_url": "https://zoom.us/j/123456789",
      "platform": "zoom"
    }
  ]
}
```

### System

#### Reboot Device

```http
POST /api/v1/system/reboot
```

#### Get Logs

```http
GET /api/v1/system/logs?lines=100&level=error
```

#### Health Check

```http
GET /api/v1/health
```

Response:

```json
{
  "status": "healthy",
  "checks": {
    "camera": "ok",
    "audio": "ok",
    "network": "ok",
    "display": "ok"
  }
}
```

## Fleet Management API

The centralized fleet management API.

### Base URL

```
https://fleet.company.com/api/v1
```

### Authentication

```http
POST /api/v1/auth/token
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "your-password"
}
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Use token in subsequent requests:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Devices

#### List Devices

```http
GET /api/v1/devices?status=online&group=building-a&limit=50&offset=0
```

Response:

```json
{
  "devices": [
    {
      "id": "croom-abc123",
      "name": "Conference Room A",
      "status": "online",
      "group": "building-a",
      "last_seen": "2024-01-15T10:30:00Z",
      "version": "1.5.0"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

#### Get Device

```http
GET /api/v1/devices/{device_id}
```

#### Update Device

```http
PATCH /api/v1/devices/{device_id}
Content-Type: application/json

{
  "name": "Executive Boardroom",
  "group": "executive",
  "tags": ["large-room", "av-equipped"]
}
```

#### Delete Device

```http
DELETE /api/v1/devices/{device_id}
```

#### Remote Actions

```http
POST /api/v1/devices/{device_id}/actions
Content-Type: application/json

{
  "action": "reboot"
}
```

Available actions:
- `reboot`
- `update`
- `join_meeting`
- `leave_meeting`
- `screenshot`
- `logs`

### Device Groups

#### List Groups

```http
GET /api/v1/groups
```

#### Create Group

```http
POST /api/v1/groups
Content-Type: application/json

{
  "name": "Building A",
  "description": "All rooms in Building A",
  "config": {
    "timezone": "America/New_York"
  }
}
```

### Configuration Policies

#### List Policies

```http
GET /api/v1/policies
```

#### Create Policy

```http
POST /api/v1/policies
Content-Type: application/json

{
  "name": "Standard Config",
  "priority": 100,
  "target": {
    "groups": ["all-rooms"]
  },
  "config": {
    "display": {
      "hdmi_cec": true
    }
  }
}
```

### Updates

#### List Available Updates

```http
GET /api/v1/updates
```

#### Deploy Update

```http
POST /api/v1/updates
Content-Type: application/json

{
  "version": "1.5.0",
  "target": {
    "devices": ["croom-abc123"]
  },
  "schedule": "2024-01-16T02:00:00Z"
}
```

### Analytics

#### Get Usage Stats

```http
GET /api/v1/analytics/usage?start=2024-01-01&end=2024-01-31&group=all
```

Response:

```json
{
  "period": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "stats": {
    "total_meetings": 1250,
    "total_duration_hours": 2500,
    "average_duration_minutes": 45,
    "platforms": {
      "google_meet": 600,
      "zoom": 400,
      "teams": 250
    },
    "peak_hours": [9, 10, 14, 15]
  }
}
```

### Webhooks

#### List Webhooks

```http
GET /api/v1/webhooks
```

#### Create Webhook

```http
POST /api/v1/webhooks
Content-Type: application/json

{
  "url": "https://company.com/croom-events",
  "events": ["device.online", "device.offline", "alert.triggered"],
  "secret": "webhook-secret"
}
```

### Alerts

#### List Alerts

```http
GET /api/v1/alerts?status=active
```

#### Acknowledge Alert

```http
POST /api/v1/alerts/{alert_id}/acknowledge
```

## WebSocket API

Real-time updates via WebSocket.

### Connect

```javascript
const ws = new WebSocket('wss://fleet.company.com/api/v1/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your-access-token'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data);
};
```

### Subscribe to Events

```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  events: ['device.status', 'meeting.started', 'meeting.ended']
}));
```

### Event Types

```json
// Device status change
{
  "type": "device.status",
  "device_id": "croom-abc123",
  "status": "online",
  "timestamp": "2024-01-15T10:30:00Z"
}

// Meeting started
{
  "type": "meeting.started",
  "device_id": "croom-abc123",
  "platform": "google_meet",
  "timestamp": "2024-01-15T10:30:00Z"
}

// Alert triggered
{
  "type": "alert.triggered",
  "alert_id": "alert123",
  "severity": "warning",
  "message": "Device offline",
  "device_id": "croom-abc123"
}
```

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "DEVICE_NOT_FOUND",
    "message": "Device with ID 'croom-xyz' not found",
    "details": {}
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or expired token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `DEVICE_OFFLINE` | 503 | Device is not reachable |
| `MEETING_ACTIVE` | 409 | Meeting already in progress |

## Rate Limiting

API requests are rate limited:

- Device API: 100 requests/minute
- Fleet API: 1000 requests/minute per user

Rate limit headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705312800
```

## SDKs

Official SDKs are available:

- [Python SDK](https://github.com/amirhmoradi/croom-python)
- [JavaScript SDK](https://github.com/amirhmoradi/croom-js)
- [Go SDK](https://github.com/amirhmoradi/croom-go)

Example (Python):

```python
from croom import CroomClient

client = CroomClient(
    base_url="http://croom.local:8080",
    api_key="your-api-key"
)

# Join meeting
client.meeting.join("https://meet.google.com/abc-defg-hij")

# Get status
status = client.status()
print(f"CPU: {status.health.cpu_percent}%")
```
