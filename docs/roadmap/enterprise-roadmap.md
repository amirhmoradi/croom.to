# Croom Roadmap

## Vision Statement

Transform Croom from a simple, cost-effective conference room solution into an enterprise-grade video conferencing platform that rivals Cisco Webex Room Kit at a fraction of the cost, while maintaining its core philosophy of simplicity and reliability.

## Target Market

- Small to medium businesses (SMBs) with 5-500 meeting rooms
- Educational institutions (schools, universities)
- Religious organizations and non-profits
- Healthcare facilities
- Government offices with budget constraints

## Core Design Principles

1. **Non-Destructive Installation:** Install on existing Raspberry Pi OS without reformatting
2. **Modern OS Support:** Compatible with latest Raspberry Pi OS (Bookworm/Trixie)
3. **Hardware Adaptive:** Features scale based on available hardware (Pi 4/5, AI accelerators)
4. **Privacy First:** All AI processing happens locally, no cloud dependency
5. **Simple Updates:** Standard apt package management, OTA updates

## Competitive Analysis

### Cisco Webex Room Kit (Enterprise Standard)
| Feature | Cisco Room Kit | Croom Current | Croom Target |
|---------|---------------|----------------|---------------|
| Hardware Cost | $3,000-15,000 | <$100 | <$250 (with AI) |
| AI Speaker Tracking | Yes | No | Phase 2 |
| Auto-Framing | Yes | No | Phase 2 |
| Multi-Platform Support | Yes | Google Meet only | Phase 1 |
| Central Management | Control Hub | None | Phase 1 |
| Local Touch UI | Yes | No | Phase 1 |
| Analytics/Monitoring | Yes | None | Phase 2 |
| Remote Troubleshooting | Yes | SSH only | Phase 2 |
| Noise Reduction | Yes | No | Phase 2 |
| Modern OS Support | N/A | Bullseye only | Phase 1 |
| Non-Destructive Install | N/A | No (requires imaging) | Phase 1 |

---

## Phase 1: Modern Foundation (Q1)

### 1.1 Modern Installation System ⭐ NEW
**Priority: P0 - Critical** | **PRD:** [PRD-007](../prd/007-modern-installation.md)

Replace image-based deployment with modern package installation:
- **One-line installer:** `curl -fsSL https://get.croom.io | bash`
- **APT packages:** Standard Debian package management
- **Non-destructive:** Install on existing Raspberry Pi OS
- **OS Support:** Bookworm (Debian 12), Trixie (Debian 13) ready
- **Hardware Support:** Raspberry Pi 4B and Pi 5 (primary targets)
- **Update system:** apt-based updates, rollback support
- **Migration:** Tools for legacy (image-based) to modern installation

**Packages:**
- `croom-core` - Agent and meeting functionality
- `croom-browser` - Chromium configuration and extensions
- `croom-ui` - Touch screen interface (optional)
- `croom-ai` - AI features (optional)

### 1.2 Touch Screen Room UI ⭐ NEW
**Priority: P1 - High** | **PRD:** [PRD-005](../prd/005-touch-screen-room-ui.md)

Local management interface for room administrators:
- **Display Support:** Official Raspberry Pi Touch Display (7"), HDMI touch displays
- **Features:**
  - Room status at a glance (next meeting, system health)
  - Meeting controls (mute, camera, leave)
  - Quick join for ad-hoc meetings
  - WiFi and network configuration
  - Audio/video device selection
  - Diagnostics and troubleshooting
- **Framework:** Qt6/QML with PySide6
- **Accessibility:** Touch-first design, remote/keyboard navigation
- **Local Web Interface:** Same UI accessible via browser at `http://croom.local:8080`

### 1.3 Management Dashboard MVP
**Priority: P0 - Critical** | **PRD:** [PRD-001](../prd/001-management-dashboard.md)

Web-based fleet management:
- Device registration and inventory
- Real-time device status monitoring
- Remote configuration management
- Credential management (encrypted)
- Bulk device provisioning
- Basic alerting (device offline, errors)

**Technical Stack:**
- Backend: Node.js/Express
- Frontend: React + TypeScript
- Database: PostgreSQL
- Real-time: WebSocket/Socket.IO

### 1.4 Multi-Platform Meeting Support
**Priority: P0 - Critical** | **PRD:** [PRD-002](../prd/002-multi-platform-support.md)

Extend beyond Google Meet:
- [x] Google Meet (current - enhancement needed)
- [ ] Microsoft Teams (browser-based)
- [ ] Zoom (browser-based)
- [ ] Webex (browser-based)

**Implementation:**
- Modular meeting provider architecture
- Calendar integration for auto-detection
- Per-room platform preference

### 1.5 Zero-Touch Device Provisioning
**Priority: P1 - High** | **PRD:** [PRD-003](../prd/003-device-provisioning.md)

Simple device setup:
- Captive portal WiFi setup
- QR code scanning for configuration
- Dashboard-based remote provisioning
- USB configuration file support

### 1.6 IR Remote Control Support
**Priority: P2 - Medium** | **Related:** Upstream PR #15

Universal remote support:
- Samsung, LG, Sony, Vizio keymaps
- Configurable key mappings
- Meeting control via remote

---

## Phase 2: Enterprise & AI Features (Q2)

### 2.1 Edge AI Features ⭐ NEW
**Priority: P1 - High** | **PRD:** [PRD-006](../prd/006-edge-ai-features.md)

Local AI processing on Raspberry Pi hardware:

**Hardware Support:**
| Hardware | TOPS | Features |
|----------|------|----------|
| Pi 5 + AI Kit (Hailo-8L) | 13 | Full AI features |
| Pi 4/5 + Coral USB | 4 | Most AI features |
| CPU only | ~1 | Basic features |

**AI Features (by priority):**
- **P0:** Person detection, noise reduction, echo cancellation
- **P1:** Auto-framing (digital zoom), speaker detection
- **P2:** PTZ speaker tracking, hand raise detection, occupancy analytics
- **P3:** Gesture recognition

**Privacy:**
- All processing local (no cloud)
- No data stored or transmitted
- Privacy mode toggle in UI

### 2.2 Advanced Monitoring & Analytics
**Priority: P1 - High** | **PRD:** [PRD-001](../prd/001-management-dashboard.md)

Comprehensive monitoring:
- Device health metrics (CPU, memory, temperature)
- Meeting quality metrics (audio/video quality)
- Room utilization analytics
- Historical data and trends
- Exportable reports

### 2.3 Security Hardening
**Priority: P0 - Critical** | **PRD:** [PRD-004](../prd/004-security-compliance.md)

Enterprise security:
- Encrypted credential storage (AES-256)
- TLS everywhere (1.3 required)
- LDAP/Active Directory integration
- SSO support (SAML, OIDC)
- MFA for dashboard
- Comprehensive audit logging
- SOC 2 Type II readiness

### 2.4 Remote Management & Troubleshooting
**Priority: P1 - High**

Enterprise-grade remote management:
- Remote reboot/shutdown
- Log collection and analysis
- Remote shell access (secure, audited)
- Configuration push (bulk updates)
- OTA software updates
- Screen capture for troubleshooting

### 2.5 Wireless Content Sharing
**Priority: P2 - Medium**

Wireless presentation:
- Miracast support
- AirPlay support
- Chrome/Edge casting
- HDMI input passthrough

---

## Phase 3: Advanced Features (Q3-Q4)

### 3.1 Advanced AI Features
**Priority: P2 - Medium** | **PRD:** [PRD-006](../prd/006-edge-ai-features.md)

Enhanced AI capabilities:
- PTZ camera speaker tracking
- Advanced pose estimation
- Meeting zone detection
- Gesture recognition (wave to start meeting)

### 3.2 Voice Control Integration
**Priority: P3 - Low**

Hands-free control (optional):
- Wake word detection (local processing)
- Voice commands (join, leave, mute)
- Privacy-first design

### 3.3 Room Booking Integration
**Priority: P2 - Medium**

Calendar and booking systems:
- Google Calendar (current)
- Microsoft 365/Exchange
- Room booking displays
- Occupancy-based room release
- Integration with booking platforms

### 3.4 Digital Signage Mode
**Priority: P3 - Low**

Idle display features:
- Company announcements
- Upcoming meetings
- Room availability status
- Custom content management

### 3.5 Advanced Interoperability
**Priority: P2 - Medium**

Enterprise integrations:
- SIP/H.323 gateway support
- PBX system integration
- Recording/streaming integration

---

## Phase 4: Scale & Polish (Q4+)

### 4.1 High Availability
- Redundant management servers
- Device failover configurations
- Offline operation capabilities
- Disaster recovery procedures

### 4.2 Multi-Tenant Support
- Organization isolation
- Role-based access control
- White-label dashboard
- Reseller/MSP support

### 4.3 Mobile Applications
- iOS and Android apps
- Device management
- Remote control
- Meeting join via mobile

### 4.4 Hardware Ecosystem
- Certified peripheral list
- Hardware bundles/kits
- OEM partnerships

---

## Hardware Requirements

### Minimum Hardware
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Raspberry Pi | Pi 4B 2GB | Pi 5 4GB |
| Storage | 16GB microSD | 32GB microSD |
| Camera | Any USB webcam | Logitech C920/C922 |
| Display (optional) | 7" touch | Official Pi Touch Display |

### For AI Features
| Feature Level | Hardware Required | Cost |
|---------------|-------------------|------|
| Basic (no AI) | Pi 4B 2GB | ~$55 |
| Standard (limited AI) | Pi 5 4GB | ~$60 |
| Full AI | Pi 5 + AI Kit | ~$130 |
| Alternative | Pi 4/5 + Coral USB | ~$115-120 |

### Supported Operating Systems
- Raspberry Pi OS Bookworm 64-bit (primary)
- Raspberry Pi OS Trixie 64-bit (coming 2025)
- Ubuntu 24.04 arm64 (secondary)

---

## Upstream Contributions

### PRs to Implement
1. **PR #15:** Samsung keymap - IR remote support foundation

### Issues to Address
1. **Issue #17:** WiFi module / ad hoc setup → PRD-003, PRD-007
2. **Issue #9:** Convert to apt packages → PRD-007
3. **Issue #6:** Dynamic device setup → PRD-003
4. **Issue #5:** Re-base on pi-gen → PRD-007 (alternative approach)

### Fork Integration (xaghy/croom)
- On-Pi setup functionality
- Documentation improvements

---

## Success Metrics

### Phase 1
- [ ] Installation works on existing Raspberry Pi OS (no reformat)
- [ ] Touch UI functional on official Pi display
- [ ] Management dashboard managing 10+ devices
- [ ] Support for 3+ meeting platforms
- [ ] Zero-touch device provisioning working

### Phase 2
- [ ] AI features running on Pi 5 + AI Kit
- [ ] Auto-framing accuracy > 90%
- [ ] Noise reduction measurably improves quality
- [ ] 99.9% device uptime achieved
- [ ] Security audit passed

### Phase 3
- [ ] PTZ speaker tracking functional
- [ ] Voice control accuracy > 95%
- [ ] Room booking integration with 3+ platforms

### Phase 4
- [ ] Supporting 1000+ devices per installation
- [ ] Multi-tenant deployment active
- [ ] Mobile apps launched

---

## Resource Requirements

### Development Team (Recommended)
- 1 Full-stack Developer (Dashboard, Touch UI)
- 1 Systems Developer (Device software, AI integration)
- 1 DevOps Engineer (Infrastructure, CI/CD, packages)
- 0.5 QA Engineer
- 0.5 Technical Writer

### Infrastructure
- Package repository (apt)
- Cloud hosting for dashboard
- CI/CD pipeline
- Device testing lab:
  - Raspberry Pi 4B (2GB, 4GB)
  - Raspberry Pi 5 (4GB, 8GB)
  - Pi AI Kit, Coral USB
  - Various touch displays
  - Multiple webcam models

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| AI accelerator availability | Medium | Medium | Support multiple (Hailo, Coral, CPU) |
| OS/API breaking changes | High | Medium | CI testing, version pinning |
| Security vulnerabilities | Critical | Medium | Security audits, rapid patching |
| Hardware performance limits | Medium | Low | Feature scaling, Pi 5 focus |
| Browser platform changes | High | Medium | Modular provider architecture |

---

## Timeline Summary

| Phase | Focus | Key Deliverables |
|-------|-------|------------------|
| **Phase 1** | Foundation | Modern install, Touch UI, Dashboard MVP, Multi-platform |
| **Phase 2** | Enterprise | Edge AI, Security, Monitoring, Remote Management |
| **Phase 3** | Advanced | PTZ tracking, Voice control, Room booking |
| **Phase 4** | Scale | HA, Multi-tenant, Mobile apps |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-15 | Claude | Initial roadmap creation |
| 2.0 | 2025-12-15 | Claude | Added Touch UI, Edge AI, Modern Installation |
