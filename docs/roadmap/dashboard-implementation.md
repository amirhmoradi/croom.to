# Management Dashboard Implementation Plan

## Overview

This document outlines the implementation plan for the PiMeet Management Dashboard, the core infrastructure component for enterprise deployment.

---

## Architecture Decision

### Technology Stack Selection

After evaluating options, the recommended stack is:

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Backend API | **Node.js + Express** | JavaScript ecosystem, async I/O, large community |
| Frontend | **React + TypeScript** | Type safety, component reuse, ecosystem |
| Database | **PostgreSQL** | Reliable, feature-rich, time-series extensions |
| Real-time | **Socket.IO** | Bi-directional, fallback support |
| Cache/Queue | **Redis** | Fast, pub/sub support |
| Device Agent | **Python 3** | Pi-native, lightweight, systemd integration |

### Alternative Considered

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Python/FastAPI | Faster API, async | Less frontend integration | Runner-up |
| Go | Performance, single binary | Smaller team familiarity | Future consideration |
| Django | Batteries included | Heavier, slower | Not selected |

---

## Project Structure

```
pimeet-dashboard/
├── README.md
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
│
├── backend/                    # API Server
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── index.ts           # Entry point
│   │   ├── config/
│   │   │   ├── database.ts
│   │   │   ├── redis.ts
│   │   │   └── auth.ts
│   │   ├── routes/
│   │   │   ├── auth.ts
│   │   │   ├── devices.ts
│   │   │   ├── config.ts
│   │   │   ├── metrics.ts
│   │   │   └── alerts.ts
│   │   ├── services/
│   │   │   ├── device.service.ts
│   │   │   ├── auth.service.ts
│   │   │   ├── metrics.service.ts
│   │   │   └── alert.service.ts
│   │   ├── models/
│   │   │   ├── device.ts
│   │   │   ├── user.ts
│   │   │   ├── metric.ts
│   │   │   └── alert.ts
│   │   ├── middleware/
│   │   │   ├── auth.ts
│   │   │   ├── validation.ts
│   │   │   └── rateLimit.ts
│   │   ├── websocket/
│   │   │   ├── index.ts
│   │   │   └── handlers.ts
│   │   └── utils/
│   │       ├── crypto.ts
│   │       └── logger.ts
│   └── tests/
│
├── frontend/                   # React Dashboard
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── index.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── devices/
│   │   │   ├── config/
│   │   │   └── metrics/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Devices.tsx
│   │   │   ├── DeviceDetail.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── Login.tsx
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── store/
│   │   └── types/
│   └── public/
│
├── agent/                      # Device Agent (Python)
│   ├── requirements.txt
│   ├── setup.py
│   ├── pimeet_agent/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── metrics.py
│   │   ├── commands.py
│   │   ├── websocket.py
│   │   └── meeting/
│   │       ├── __init__.py
│   │       ├── provider.py
│   │       ├── google_meet.py
│   │       ├── teams.py
│   │       └── zoom.py
│   ├── tests/
│   └── pimeet-agent.service    # systemd unit
│
├── migrations/                 # Database migrations
│   ├── 001_initial.sql
│   ├── 002_devices.sql
│   └── 003_metrics.sql
│
└── scripts/
    ├── setup.sh
    ├── deploy.sh
    └── backup.sh
```

---

## Database Schema

### Core Tables

```sql
-- Users and authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    mfa_secret VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Devices
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mac_address VARCHAR(17) UNIQUE NOT NULL,
    hostname VARCHAR(255),
    name VARCHAR(255),
    location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'offline',
    last_seen TIMESTAMP,
    agent_version VARCHAR(50),
    os_version VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Device groups
CREATE TABLE device_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES device_groups(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE device_group_members (
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    group_id UUID REFERENCES device_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (device_id, group_id)
);

-- Device configuration
CREATE TABLE device_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    config JSONB NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    applied_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Credentials (encrypted)
CREATE TABLE credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    encrypted_data BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Metrics (time-series)
CREATE TABLE device_metrics (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    cpu_usage FLOAT,
    memory_usage FLOAT,
    temperature FLOAT,
    disk_usage FLOAT,
    network_latency FLOAT
);

-- Convert to hypertable if using TimescaleDB
-- SELECT create_hypertable('device_metrics', 'time');

-- Alerts
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    condition JSONB NOT NULL,
    severity VARCHAR(50) NOT NULL,
    channels JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES alert_rules(id),
    device_id UUID REFERENCES devices(id),
    status VARCHAR(50) DEFAULT 'active',
    message TEXT,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP
);

-- Audit log
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    actor_id UUID REFERENCES users(id),
    actor_email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB,
    ip_address INET
);

-- Indexes
CREATE INDEX idx_devices_status ON devices(status);
CREATE INDEX idx_devices_last_seen ON devices(last_seen);
CREATE INDEX idx_device_metrics_device_time ON device_metrics(device_id, time DESC);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
```

---

## API Endpoints

### Authentication
```
POST   /api/v1/auth/login           # Login
POST   /api/v1/auth/logout          # Logout
POST   /api/v1/auth/refresh         # Refresh token
POST   /api/v1/auth/mfa/setup       # Setup MFA
POST   /api/v1/auth/mfa/verify      # Verify MFA code
```

### Devices
```
GET    /api/v1/devices              # List devices
POST   /api/v1/devices              # Register device
GET    /api/v1/devices/:id          # Get device
PUT    /api/v1/devices/:id          # Update device
DELETE /api/v1/devices/:id          # Delete device
POST   /api/v1/devices/:id/actions  # Execute action (restart, etc.)
GET    /api/v1/devices/:id/logs     # Get device logs
```

### Configuration
```
GET    /api/v1/devices/:id/config   # Get device config
PUT    /api/v1/devices/:id/config   # Update device config
GET    /api/v1/config-templates     # List templates
POST   /api/v1/config-templates     # Create template
PUT    /api/v1/config-templates/:id # Update template
DELETE /api/v1/config-templates/:id # Delete template
```

### Metrics
```
GET    /api/v1/devices/:id/metrics  # Get device metrics
GET    /api/v1/metrics/aggregate    # Aggregated metrics
GET    /api/v1/metrics/export       # Export metrics
```

### Alerts
```
GET    /api/v1/alerts               # List alerts
PUT    /api/v1/alerts/:id           # Update alert (acknowledge)
GET    /api/v1/alert-rules          # List rules
POST   /api/v1/alert-rules          # Create rule
PUT    /api/v1/alert-rules/:id      # Update rule
DELETE /api/v1/alert-rules/:id      # Delete rule
```

### Users (Admin only)
```
GET    /api/v1/users                # List users
POST   /api/v1/users                # Create user
PUT    /api/v1/users/:id            # Update user
DELETE /api/v1/users/:id            # Delete user
```

---

## WebSocket Protocol

### Connection
```javascript
// Client connects
socket.connect('wss://dashboard/ws', {
  auth: { token: 'jwt-token' }
});
```

### Events (Server → Client)
```javascript
// Device status update
{ event: 'device:status', data: { id, status, last_seen } }

// New metric
{ event: 'device:metric', data: { device_id, metrics } }

// Alert triggered
{ event: 'alert:new', data: { alert } }

// Alert resolved
{ event: 'alert:resolved', data: { alert_id } }
```

### Events (Client → Server)
```javascript
// Subscribe to device updates
{ event: 'subscribe', data: { devices: ['id1', 'id2'] } }

// Unsubscribe
{ event: 'unsubscribe', data: { devices: ['id1'] } }

// Execute command
{ event: 'command', data: { device_id, action, params } }
```

---

## Device Agent Design

### Core Components

```python
# Main agent loop
class PiMeetAgent:
    def __init__(self, config):
        self.config = config
        self.ws_client = WebSocketClient(config.dashboard_url)
        self.metrics_collector = MetricsCollector()
        self.command_handler = CommandHandler()
        self.meeting_manager = MeetingManager()

    async def run(self):
        await self.ws_client.connect()
        await asyncio.gather(
            self.heartbeat_loop(),
            self.metrics_loop(),
            self.command_loop(),
            self.meeting_loop()
        )

    async def heartbeat_loop(self):
        while True:
            await self.ws_client.send_heartbeat()
            await asyncio.sleep(30)

    async def metrics_loop(self):
        while True:
            metrics = await self.metrics_collector.collect()
            await self.ws_client.send_metrics(metrics)
            await asyncio.sleep(60)
```

### Metrics Collection

```python
class MetricsCollector:
    async def collect(self):
        return {
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'temperature': self._get_cpu_temp(),
            'disk_usage': psutil.disk_usage('/').percent,
            'network': self._get_network_stats()
        }

    def _get_cpu_temp(self):
        try:
            with open('/sys/class/thermal/thermal_zone0/temp') as f:
                return int(f.read()) / 1000
        except:
            return None
```

### Command Handler

```python
class CommandHandler:
    async def handle(self, command):
        handlers = {
            'restart': self.restart,
            'update': self.update,
            'reboot': self.reboot,
            'screenshot': self.screenshot,
            'logs': self.get_logs
        }
        handler = handlers.get(command['action'])
        if handler:
            return await handler(command.get('params', {}))
        raise ValueError(f"Unknown command: {command['action']}")

    async def restart(self, params):
        subprocess.run(['sudo', 'systemctl', 'restart', 'pimeet-browser'])
        return {'success': True}

    async def screenshot(self, params):
        # Capture screen using scrot
        subprocess.run(['scrot', '/tmp/screenshot.png'])
        with open('/tmp/screenshot.png', 'rb') as f:
            return {'image': base64.b64encode(f.read()).decode()}
```

---

## Implementation Phases

### Sprint 1: Infrastructure (Week 1-2)

**Backend:**
- [ ] Project setup (TypeScript, Express)
- [ ] Database schema and migrations
- [ ] Basic authentication (JWT)
- [ ] Device CRUD endpoints

**Frontend:**
- [ ] Project setup (React, TypeScript)
- [ ] Login page
- [ ] Basic layout and navigation
- [ ] Device list page

**DevOps:**
- [ ] Docker configuration
- [ ] CI/CD pipeline setup
- [ ] Development environment

### Sprint 2: Core Features (Week 3-4)

**Backend:**
- [ ] WebSocket server
- [ ] Metrics ingestion
- [ ] Device configuration API
- [ ] Basic alerting

**Frontend:**
- [ ] Device detail page
- [ ] Real-time status updates
- [ ] Configuration editor
- [ ] Metrics dashboard

**Agent:**
- [ ] Basic agent structure
- [ ] Dashboard connection
- [ ] Metrics reporting
- [ ] Command handling

### Sprint 3: Polish (Week 5-6)

**Backend:**
- [ ] User management
- [ ] Audit logging
- [ ] Alert channels (email)
- [ ] API documentation

**Frontend:**
- [ ] Settings pages
- [ ] Alert management
- [ ] User management
- [ ] Responsive design

**Agent:**
- [ ] Robust reconnection
- [ ] Configuration sync
- [ ] Update mechanism

### Sprint 4: Testing & Launch (Week 7-8)

- [ ] Integration testing
- [ ] Security review
- [ ] Performance testing
- [ ] Documentation
- [ ] Beta deployment
- [ ] Bug fixes

---

## Security Considerations

### Authentication
- JWT tokens with short expiry (15 min)
- Refresh tokens (7 days, rotated on use)
- MFA required for admin accounts
- Password hashing with bcrypt

### API Security
- Rate limiting (100 req/min per IP)
- Input validation (Joi/Zod)
- SQL injection prevention (parameterized queries)
- XSS prevention (React + CSP headers)

### Device Communication
- mTLS for device authentication
- Device certificates signed by internal CA
- Certificate rotation support

### Credential Storage
- AES-256-GCM encryption
- Per-device encryption keys
- Master key in environment variable (production: KMS)

---

## Deployment

### Docker Compose (Development)
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://pimeet:password@db:5432/pimeet
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  frontend:
    build: ./frontend
    ports:
      - "80:80"

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=pimeet
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=pimeet

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Production Checklist
- [ ] TLS certificates configured
- [ ] Environment variables secured
- [ ] Database backups configured
- [ ] Monitoring enabled
- [ ] Log aggregation setup
- [ ] Rate limiting tuned
- [ ] Resource limits set

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time | <200ms (p95) | APM monitoring |
| Dashboard Load | <3s | Browser timing |
| WebSocket Latency | <100ms | Custom metrics |
| Device Update Delay | <30s | End-to-end test |
| Concurrent Devices | 1000+ | Load testing |

---

## Next Steps

1. **Review and approve** this implementation plan
2. **Set up repositories** for backend, frontend, agent
3. **Initialize projects** with chosen technologies
4. **Begin Sprint 1** implementation
5. **Weekly progress reviews**

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-15 | 1.0 | Initial implementation plan |
