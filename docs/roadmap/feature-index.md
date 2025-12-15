# Feature Index

## Overview

Quick reference for all planned features with their status, priority, and documentation links.

---

## Feature Status Legend

| Status | Description |
|--------|-------------|
| Planned | Not started |
| In Progress | Active development |
| Testing | Development complete, in testing |
| Complete | Released |
| On Hold | Deferred |

## Priority Legend

| Priority | Description |
|----------|-------------|
| P0 | Critical - Must have for MVP |
| P1 | High - Should have |
| P2 | Medium - Nice to have |
| P3 | Low - Future consideration |

---

## Phase 1: Modern Foundation

### Installation & OS Compatibility ⭐ NEW

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| One-line installer | P0 | Complete | [PRD-007](../prd/007-modern-installation.md) | `curl \| bash` |
| APT package repository | P0 | Complete | [PRD-007](../prd/007-modern-installation.md) | Debian packages |
| Bookworm OS support | P0 | Complete | [PRD-007](../prd/007-modern-installation.md) | Debian 12 |
| Trixie OS support | P1 | Complete | [PRD-007](../prd/007-modern-installation.md) | Debian 13 (2025) |
| Raspberry Pi 5 support | P0 | Complete | [PRD-007](../prd/007-modern-installation.md) | Primary target |
| Raspberry Pi 4B support | P0 | Complete | [PRD-007](../prd/007-modern-installation.md) | Primary target |
| Non-destructive install | P0 | Complete | [PRD-007](../prd/007-modern-installation.md) | Preserve user data |
| apt update system | P1 | Complete | [PRD-007](../prd/007-modern-installation.md) | Standard updates |
| Rollback support | P2 | Complete | [PRD-007](../prd/007-modern-installation.md) | Version downgrade |
| Legacy migration tool | P2 | Complete | [PRD-007](../prd/007-modern-installation.md) | Image→Package |

### Touch Screen Room UI ⭐ NEW

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Official Pi Display support | P0 | Complete | [PRD-005](../prd/005-touch-screen-room-ui.md) | 7" DSI |
| HDMI touch display support | P1 | Complete | [PRD-005](../prd/005-touch-screen-room-ui.md) | Various sizes |
| Home/status screen | P0 | Complete | [PRD-005](../prd/005-touch-screen-room-ui.md) | Room status |
| Meeting controls | P0 | Complete | [PRD-005](../prd/005-touch-screen-room-ui.md) | Mute, camera, leave |
| Quick join screen | P0 | Complete | [PRD-005](../prd/005-touch-screen-room-ui.md) | Ad-hoc meetings |
| On-screen keyboard | P0 | Complete | [PRD-005](../prd/005-touch-screen-room-ui.md) | Touch input |
| Settings screens | P1 | Complete | [PRD-005](../prd/005-touch-screen-room-ui.md) | Room/network config |
| Diagnostics screen | P1 | Complete | [PRD-005](../prd/005-touch-screen-room-ui.md) | System health |
| Local web interface | P1 | Complete | [PRD-005](../prd/005-touch-screen-room-ui.md) | Browser access |
| IR remote navigation | P2 | Complete | [PRD-005](../prd/005-touch-screen-room-ui.md) | TV remote support |
| Admin PIN protection | P1 | Complete | [PRD-005](../prd/005-touch-screen-room-ui.md) | Secure settings |

### Management Dashboard

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Device registration | P0 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Add devices |
| Device inventory | P0 | Complete | [PRD-001](../prd/001-management-dashboard.md) | List/search |
| Real-time status | P0 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Online/offline |
| Configuration management | P0 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Remote config |
| Credential vault | P0 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Encrypted storage |
| Basic alerting | P1 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Email/Slack/Teams/MQTT |
| User management | P1 | Complete | [PRD-001](../prd/001-management-dashboard.md) | RBAC |

### Multi-Platform Support

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Google Meet | P0 | Complete | [PRD-002](../prd/002-multi-platform-support.md) | Playwright-based |
| Microsoft Teams | P0 | Complete | [PRD-002](../prd/002-multi-platform-support.md) | Browser-based |
| Zoom | P1 | Complete | [PRD-002](../prd/002-multi-platform-support.md) | Browser-based |
| Webex | P2 | Complete | [PRD-002](../prd/002-multi-platform-support.md) | Browser-based |
| Platform auto-detection | P0 | Complete | [PRD-002](../prd/002-multi-platform-support.md) | From calendar |
| Provider architecture | P0 | Complete | [PRD-002](../prd/002-multi-platform-support.md) | Modular design |

### Device Provisioning

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Captive portal setup | P0 | Complete | [PRD-003](../prd/003-device-provisioning.md) | WiFi AP mode |
| USB configuration | P1 | Complete | [PRD-003](../prd/003-device-provisioning.md) | Config file |
| QR code setup | P2 | Complete | [PRD-003](../prd/003-device-provisioning.md) | Scan to configure |
| Dashboard registration | P1 | Complete | [PRD-003](../prd/003-device-provisioning.md) | Auto-register |
| 802.1X WiFi support | P2 | Complete | [PRD-003](../prd/003-device-provisioning.md) | Enterprise WiFi |

### IR Remote Control

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Samsung keymap | P2 | Planned | [Upstream PR #15](upstream-contributions.md) | Foundation |
| LG keymap | P2 | Planned | - | Extend |
| Sony keymap | P2 | Planned | - | Extend |
| Custom keymaps | P3 | Planned | - | User configurable |
| Meeting controls | P2 | Planned | - | Mute, volume, end |

---

## Phase 2: Enterprise & AI Features

### Edge AI Features ⭐ NEW

| Feature | Priority | Status | PRD | Hardware |
|---------|----------|--------|-----|----------|
| Person detection | P0 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | All |
| Noise reduction | P0 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | CPU (RNNoise) |
| Echo cancellation | P0 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | CPU (Speex) |
| Face detection | P1 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | All |
| Auto-framing (digital) | P1 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | All |
| Speaker detection | P1 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | All |
| Occupancy counting | P2 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | All |
| Hand raise detection | P2 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | AI accelerator |
| PTZ speaker tracking | P2 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | AI + PTZ camera |
| Gesture recognition | P3 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | AI accelerator |
| Pi AI Kit (Hailo) support | P0 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | 13 TOPS |
| Coral USB support | P1 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | 4 TOPS |
| CPU fallback | P1 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | Basic features |
| Privacy mode | P1 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | Disable AI |

### Security & Compliance

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Credential encryption | P0 | Complete | [PRD-004](../prd/004-security-compliance.md) | AES-256-GCM |
| TLS 1.3 | P0 | Complete | [PRD-004](../prd/004-security-compliance.md) | All connections |
| MFA | P0 | Complete | [PRD-004](../prd/004-security-compliance.md) | TOTP, WebAuthn |
| SAML SSO | P1 | Complete | [PRD-004](../prd/004-security-compliance.md) | Enterprise auth |
| OIDC SSO | P1 | Complete | [PRD-004](../prd/004-security-compliance.md) | Enterprise auth |
| LDAP integration | P1 | Complete | [PRD-004](../prd/004-security-compliance.md) | AD/LDAP |
| RBAC | P1 | Complete | [PRD-004](../prd/004-security-compliance.md) | 6 default roles |
| Audit logging | P0 | Complete | [PRD-004](../prd/004-security-compliance.md) | Tamper-evident |
| JWT API Auth | P0 | Complete | [PRD-004](../prd/004-security-compliance.md) | API security |
| Rate limiting | P1 | Complete | [PRD-004](../prd/004-security-compliance.md) | Per-client limits |
| SOC 2 readiness | P2 | Complete | [PRD-004](../prd/004-security-compliance.md) | Compliance |

### Monitoring & Analytics

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Device health metrics | P1 | Complete | [PRD-001](../prd/001-management-dashboard.md) | CPU/memory/temp |
| Meeting quality metrics | P1 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Audio/video |
| Room utilization | P2 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Analytics |
| Report generation | P2 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Daily/Weekly |
| SIEM integration | P2 | Complete | [PRD-004](../prd/004-security-compliance.md) | CEF/LEEF/JSON |
| Alerting system | P1 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Email/Slack/Teams/MQTT |
| Performance trends | P2 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Time-series analysis |

### Remote Management

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Remote reboot | P1 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Device control |
| Remote shell | P2 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Whitelisted commands |
| Log collection | P1 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Support bundles |
| Screen capture | P2 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Remote view |
| OTA updates | P1 | Complete | [PRD-007](../prd/007-modern-installation.md) | Remote deploy |
| Diagnostics | P1 | Complete | [PRD-001](../prd/001-management-dashboard.md) | System tests |
| Service restart | P1 | Complete | [PRD-001](../prd/001-management-dashboard.md) | Remote control |

### Wireless Content Sharing

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Miracast | P2 | Planned | [Roadmap](enterprise-roadmap.md) | Windows/Android |
| AirPlay | P2 | Planned | [Roadmap](enterprise-roadmap.md) | Apple devices |
| Chromecast | P2 | Planned | [Roadmap](enterprise-roadmap.md) | Chrome browser |

---

## Phase 3: Advanced Features

### Advanced AI

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| PTZ speaker tracking | P2 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | VISCA protocol |
| Meeting zones | P2 | Complete | [PRD-006](../prd/006-edge-ai-features.md) | Region detection |
| Advanced gestures | P3 | Planned | [PRD-006](../prd/006-edge-ai-features.md) | Wave to start |

### Voice Control

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Wake word detection | P3 | Planned | [Roadmap](enterprise-roadmap.md) | Local processing |
| Voice commands | P3 | Planned | [Roadmap](enterprise-roadmap.md) | Join/leave/mute |

### Room Booking

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Google Calendar | P0 | Complete | [Roadmap](enterprise-roadmap.md) | OAuth2 + Service Account |
| Microsoft 365 | P2 | Complete | [Roadmap](enterprise-roadmap.md) | Graph API + MSAL |
| Booking displays | P3 | Planned | [Roadmap](enterprise-roadmap.md) | External displays |
| Occupancy release | P3 | Planned | [Roadmap](enterprise-roadmap.md) | Auto-release empty |

### Digital Signage

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Idle screen content | P3 | Planned | [Roadmap](enterprise-roadmap.md) | Announcements |
| Meeting schedule | P3 | Planned | [Roadmap](enterprise-roadmap.md) | Today's meetings |
| Room status | P3 | Planned | [Roadmap](enterprise-roadmap.md) | Available/busy |

---

## Phase 4: Scale & Polish

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| High availability | P2 | Planned | [Roadmap](enterprise-roadmap.md) | Dashboard HA |
| Multi-tenant | P2 | Planned | [Roadmap](enterprise-roadmap.md) | MSP support |
| White-label | P3 | Planned | [Roadmap](enterprise-roadmap.md) | Custom branding |
| Mobile app (iOS) | P3 | Planned | [Roadmap](enterprise-roadmap.md) | Device management |
| Mobile app (Android) | P3 | Planned | [Roadmap](enterprise-roadmap.md) | Device management |

---

## x86_64/PC Hardware Support ⭐ NEW

### Linux x86_64 Platform Support

| Feature | Priority | Status | Notes |
|---------|----------|--------|-------|
| Intel NUC support | P1 | Complete | Mini PC deployment |
| Generic x86_64 PC | P1 | Complete | Desktop/server class |
| Ubuntu 22.04/24.04 | P1 | Complete | LTS releases |
| Debian 12/13 | P1 | Complete | Bookworm/Trixie |
| NVIDIA GPU acceleration | P1 | Complete | TensorRT + CUDA |
| Intel OpenVINO | P1 | Complete | CPU + iGPU |
| DDC/CI display control | P1 | Complete | Monitor control |
| USB webcam support | P0 | Complete | Logitech, etc. |
| StubGPIO for PC | P1 | Complete | Graceful fallback |
| Hardware profiles | P1 | Complete | Auto-detection |

### x86_64 AI Acceleration

| Accelerator | TOPS | Status | Notes |
|-------------|------|--------|-------|
| NVIDIA RTX 4090 | 80+ | Supported | TensorRT FP16 |
| NVIDIA RTX 3080 | 40 | Supported | TensorRT |
| NVIDIA RTX 3060 | 20 | Supported | TensorRT |
| Intel Arc A770 | 20 | Supported | OpenVINO |
| Intel Iris Xe | 5 | Supported | OpenVINO |
| Intel UHD | 2 | Supported | OpenVINO |
| Google Coral USB | 4 | Supported | Edge TPU |
| CPU (AVX2/AVX-512) | 0.5 | Fallback | ONNX Runtime |

### x86_64 Use Cases

| Use Case | Hardware | Notes |
|----------|----------|-------|
| Conference room | Intel NUC | Small form factor |
| Meeting room | Mini PC | Cost-effective |
| Training room | Desktop + GPU | High performance |
| Enterprise server | Server | VM/container |
| Development | Any x86_64 | Testing/dev |

---

## Hardware Support Matrix

| Hardware | Status | Notes |
|----------|--------|-------|
| **Raspberry Pi** | | |
| Raspberry Pi 5 (4GB/8GB) | Primary | Best performance |
| Raspberry Pi 4B (4GB/8GB) | Primary | Widely deployed |
| Raspberry Pi 4B (2GB) | Secondary | Limited AI |
| Raspberry Pi 3B+ | Limited | No AI, basic only |
| **x86_64 Systems** | | |
| Intel NUC | Primary | Mini PC target |
| Generic x86_64 PC | Supported | Desktop/Server |
| NVIDIA Jetson | Supported | ARM64 + NVIDIA |
| **AI Accelerators** | | |
| Pi AI Kit (Hailo-8L) | Primary | 13 TOPS |
| NVIDIA GPU (x86_64) | Primary | TensorRT |
| Intel GPU (OpenVINO) | Supported | iGPU/Arc |
| Coral USB Accelerator | Secondary | 4 TOPS |
| **Displays** | | |
| Official 7" Touch | Primary | Full UI support |
| HDMI Touch Displays | Secondary | Varies by model |
| DDC/CI Monitors | Supported | x86_64 only |
| **Cameras** | | |
| Logitech C920/C922 | Recommended | USB webcam |
| Logitech BRIO | Recommended | 4K USB |
| Microsoft LifeCam | Supported | USB webcam |
| PTZ Cameras | Optional | Speaker tracking |
| Raspberry Pi Camera | Supported | Pi only |

---

## OS Support Matrix

| Operating System | Architecture | Status | Notes |
|------------------|--------------|--------|-------|
| **Raspberry Pi OS** | | | |
| Bookworm (64-bit) | arm64 | Primary | Current stable |
| Trixie (64-bit) | arm64 | Supported | Debian 13 |
| Bookworm (32-bit) | armhf | Limited | Pi 3/Zero 2 |
| **Debian** | | | |
| Debian 12 (Bookworm) | amd64 | Primary | x86_64 target |
| Debian 13 (Trixie) | amd64 | Supported | Testing |
| **Ubuntu** | | | |
| Ubuntu 22.04 LTS (Jammy) | amd64 | Primary | Long-term support |
| Ubuntu 24.04 LTS (Noble) | amd64 | Primary | Latest LTS |
| Ubuntu 24.04 arm64 | arm64 | Secondary | Server option |

---

## Document References

### Product Requirements
- [PRD-001: Management Dashboard](../prd/001-management-dashboard.md)
- [PRD-002: Multi-Platform Support](../prd/002-multi-platform-support.md)
- [PRD-003: Device Provisioning](../prd/003-device-provisioning.md)
- [PRD-004: Security & Compliance](../prd/004-security-compliance.md)
- [PRD-005: Touch Screen Room UI](../prd/005-touch-screen-room-ui.md) ⭐ NEW
- [PRD-006: Edge AI Features](../prd/006-edge-ai-features.md) ⭐ NEW
- [PRD-007: Modern Installation](../prd/007-modern-installation.md) ⭐ NEW

### Planning Documents
- [Enterprise Roadmap](enterprise-roadmap.md)
- [Upstream Contributions](upstream-contributions.md)
- [Dashboard Implementation](dashboard-implementation.md)

### Guides
- [User Guide](../guides/user-guide.md)
- [Administrator Guide](../guides/administrator-guide.md)
- [Deployment Guide](../guides/deployment-guide.md)

---

## Version History

| Date | Changes |
|------|---------|
| 2025-12-15 | Initial feature index creation |
| 2025-12-15 | Added Touch UI, Edge AI, Modern Installation features |
| 2025-12-15 | Implemented core services: Calendar, Audio, Video, Display, Dashboard Client |
| 2025-12-15 | Completed Phase 1 implementation (Touch UI, Dashboard, Multi-Platform) |
| 2025-12-15 | Completed AI backends (Hailo, Coral, ONNX CPU) |
| 2025-12-15 | Completed Calendar integration (Google + Microsoft 365) |
| 2025-12-15 | Implemented PRD-003: Device Provisioning (captive portal, USB config, setup wizard) |
| 2025-12-15 | Implemented PRD-004: Security & Compliance (encryption, MFA, SSO, RBAC, audit) |
| 2025-12-15 | Completed PRD-001: Monitoring & Alerting (alerting system, remote ops, analytics) |
| 2025-12-15 | Completed PRD-002: Meeting Controls (screen share, reactions, recording, quality) |
| 2025-12-15 | Completed PRD-005: Touch UI Components (buttons, cards, meeting controls, keyboard) |
| 2025-12-15 | Completed PRD-006: AI Features (auto-framing, speaker tracking, PTZ control) |
| 2025-12-15 | Completed PRD-007: Installation System (component installer, dependency management) |
| 2025-12-15 | Completed PRD-008: Cross-Platform HAL (GPIO, I2C, Camera, Display abstraction) |
| 2025-12-15 | **x86_64 Linux Hardware Expansion:** |
| 2025-12-15 | - Enhanced platform detector with Intel/AMD GPU detection |
| 2025-12-15 | - Added StubGPIO for systems without GPIO hardware |
| 2025-12-15 | - Implemented DDC/CI display control for x86_64 monitors |
| 2025-12-15 | - Added NVIDIA TensorRT AI backend for GPU acceleration |
| 2025-12-15 | - Created Intel OpenVINO AI backend for CPU/iGPU |
| 2025-12-15 | - Updated installer packaging for x86_64 (Debian/Ubuntu) |
| 2025-12-15 | - Created hardware profiles for x86_64, NUC, NVIDIA, Intel |
| 2025-12-15 | - Added USB camera auto-configuration service |
