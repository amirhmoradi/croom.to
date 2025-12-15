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
| P0 | Critical - Must have |
| P1 | High - Should have |
| P2 | Medium - Nice to have |
| P3 | Low - Future consideration |

---

## Phase 1: Foundation & Multi-Platform

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Management Dashboard | P0 | Planned | [PRD-001](../prd/001-management-dashboard.md) | Core infrastructure |
| Device Registration | P0 | Planned | [PRD-001](../prd/001-management-dashboard.md) | Part of dashboard |
| Real-time Monitoring | P0 | Planned | [PRD-001](../prd/001-management-dashboard.md) | Part of dashboard |
| Google Meet (current) | P0 | Complete | [PRD-002](../prd/002-multi-platform-support.md) | Enhancement needed |
| Microsoft Teams | P0 | Planned | [PRD-002](../prd/002-multi-platform-support.md) | High priority |
| Zoom | P1 | Planned | [PRD-002](../prd/002-multi-platform-support.md) | |
| Webex | P2 | Planned | [PRD-002](../prd/002-multi-platform-support.md) | |
| Captive Portal Setup | P0 | Planned | [PRD-003](../prd/003-device-provisioning.md) | Primary provisioning |
| USB Configuration | P1 | Planned | [PRD-003](../prd/003-device-provisioning.md) | Offline setup |
| IR Remote Control | P2 | Planned | [Upstream PR #15](upstream-contributions.md) | Samsung keymap base |
| Dynamic Device Setup | P1 | Planned | [PRD-003](../prd/003-device-provisioning.md) | Upstream Issue #6 |

---

## Phase 2: Enterprise Features

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Advanced Monitoring | P1 | Planned | [PRD-001](../prd/001-management-dashboard.md) | Extended metrics |
| Analytics Dashboard | P1 | Planned | [PRD-001](../prd/001-management-dashboard.md) | Usage analytics |
| Remote Troubleshooting | P1 | Planned | [PRD-001](../prd/001-management-dashboard.md) | Log access, screenshots |
| Credential Encryption | P0 | Planned | [PRD-004](../prd/004-security-compliance.md) | Security requirement |
| MFA/SSO Integration | P0 | Planned | [PRD-004](../prd/004-security-compliance.md) | Enterprise auth |
| RBAC | P1 | Planned | [PRD-004](../prd/004-security-compliance.md) | Access control |
| Audit Logging | P0 | Planned | [PRD-004](../prd/004-security-compliance.md) | Compliance |
| Wireless Content Sharing | P2 | Planned | [Roadmap](enterprise-roadmap.md) | AirPlay/Miracast |
| APT Packages | P2 | Planned | [Upstream Issue #9](upstream-contributions.md) | Better updates |

---

## Phase 3: AI & Advanced

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| Speaker Tracking | P2 | Planned | [Roadmap](enterprise-roadmap.md) | Requires PTZ camera |
| Auto-Framing | P2 | Planned | [Roadmap](enterprise-roadmap.md) | AI-powered |
| Voice Control | P3 | Planned | [Roadmap](enterprise-roadmap.md) | Wake word detection |
| Room Booking Integration | P2 | Planned | [Roadmap](enterprise-roadmap.md) | Calendar integration |
| Digital Signage | P3 | Planned | [Roadmap](enterprise-roadmap.md) | Idle display |

---

## Phase 4: Scale & Polish

| Feature | Priority | Status | PRD | Notes |
|---------|----------|--------|-----|-------|
| High Availability | P2 | Planned | [Roadmap](enterprise-roadmap.md) | Dashboard HA |
| Multi-Tenant Support | P2 | Planned | [Roadmap](enterprise-roadmap.md) | MSP support |
| Mobile Applications | P3 | Planned | [Roadmap](enterprise-roadmap.md) | iOS/Android |
| Hardware Partnerships | P3 | Planned | [Roadmap](enterprise-roadmap.md) | OEM bundles |

---

## Current Sprint Focus

### Immediate Priorities (Next 4 Weeks)

1. **Management Dashboard MVP**
   - Device registration
   - Basic monitoring
   - Configuration management
   - Simple alerting

2. **Zero-Touch Provisioning**
   - Captive portal setup
   - Generic base image
   - Dashboard registration

3. **Teams Support**
   - Browser-based implementation
   - Authentication flow
   - Calendar integration

---

## Feature Dependencies

```
Management Dashboard MVP
├── Database Setup
├── API Development
├── Frontend Development
└── Device Agent
    └── Zero-Touch Provisioning
        ├── Captive Portal
        └── Dashboard Registration

Multi-Platform Support
├── Platform Provider Architecture
├── Google Meet (existing)
├── Microsoft Teams (new)
├── Zoom (new)
└── Calendar Integration

Security & Compliance
├── Credential Encryption
├── TLS Configuration
├── Authentication (MFA/SSO)
└── Audit Logging
```

---

## Feature Requests Backlog

Features requested but not yet scheduled:

| Request | Source | Consideration |
|---------|--------|---------------|
| SIP/H.323 support | Enterprise | Phase 3+ |
| Recording integration | Multiple | Need investigation |
| Physical room presence | Enterprise | IoT sensor integration |
| Multi-language support | International | UI localization |
| Custom branding | Enterprise | White-label option |

---

## Document References

### Product Requirements
- [PRD-001: Management Dashboard](../prd/001-management-dashboard.md)
- [PRD-002: Multi-Platform Support](../prd/002-multi-platform-support.md)
- [PRD-003: Device Provisioning](../prd/003-device-provisioning.md)
- [PRD-004: Security & Compliance](../prd/004-security-compliance.md)

### Planning Documents
- [Enterprise Roadmap](enterprise-roadmap.md)
- [Upstream Contributions](upstream-contributions.md)

### Guides
- [User Guide](../guides/user-guide.md)
- [Administrator Guide](../guides/administrator-guide.md)
- [Deployment Guide](../guides/deployment-guide.md)

---

## Version History

| Date | Changes |
|------|---------|
| 2025-12-15 | Initial feature index creation |
