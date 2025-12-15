# Upstream Contributions Tracking

## Overview

This document tracks contributions to and from upstream repositories:
- **Main Upstream:** [pmansour/pimeet](https://github.com/pmansour/pimeet)
- **Fork Reference:** [xaghy/pimeet](https://github.com/xaghy/pimeet)

---

## Pull Requests to Implement

### From pmansour/pimeet

#### PR #15: Samsung Keymap File
**Status:** Open (pending implementation)
**Author:** behoyh
**Created:** December 14, 2022

**Description:**
Adds infrared remote control support for Samsung TVs using ir-keytable.

**Key Changes:**
- Creates Samsung keymap file with NEC protocol IR codes
- Maps remote buttons to keyboard inputs:
  - Up → KEY_UP
  - Down → KEY_DOWN
  - Left → Shift+Tab
  - Right → Tab
  - Enter → KEY_ENTER

**Implementation Requirements:**
1. Install ir-keytable
2. Enable GPIO IR in boot config
3. Create keymap file at `/etc/rc_keymaps/samsung`
4. Add keytable command to startup

**Our Implementation Plan:**
- [ ] Implement as base for universal remote support
- [ ] Extend to support multiple TV brands
- [ ] Create configurable keymap system
- [ ] Add meeting-specific key bindings (mute, end call)

**Priority:** Phase 1 (P2 - Medium)

---

## Issues to Address

### Issue #17: WiFi Module / Ad Hoc WiFi Setup
**Status:** Open
**Author:** bsymain
**Created:** August 13, 2025

**Description:**
Request for WiFi module functionality and ad hoc network setup capabilities.

**Our Implementation:**
Addressed in PRD-003 (Device Provisioning):
- Captive portal WiFi setup
- WiFi AP mode for initial configuration
- Dynamic WiFi reconfiguration

**Status:** In Progress (Phase 1)

---

### Issue #9: Convert Scripts to APT Packages
**Status:** Open
**Author:** pmansour
**Created:** March 6, 2022
**Labels:** enhancement, size:L
**Milestone:** "Software components can be updated without toil"

**Description:**
Convert existing scripts and applications into Debian packages for easier distribution and updates.

**Benefits:**
- Easier updates via apt
- Better dependency management
- Standard Linux package management
- Version tracking

**Our Implementation Plan:**
- [ ] Create pimeet-agent package
- [ ] Create pimeet-browser package
- [ ] Create pimeet-config package
- [ ] Set up apt repository
- [ ] Implement OTA updates

**Priority:** Phase 1 (P2 - Medium)

---

### Issue #6: Allow Dynamic Setup of Devices
**Status:** Open
**Author:** pmansour
**Created:** March 6, 2022
**Labels:** enhancement, size:XL

**Description:**
Support flexible device configuration rather than static setups baked into images.

**Our Implementation:**
Fully addressed in PRD-003 (Device Provisioning):
- Zero-touch provisioning
- Captive portal setup
- USB configuration
- Dashboard-driven configuration
- QR code setup

**Status:** Primary focus of Phase 1

---

### Issue #5: Re-base on pi-gen Tool
**Status:** Open
**Author:** pmansour
**Created:** March 6, 2022
**Labels:** enhancement, size:M
**Milestone:** "Pimeet codebase is easy to maintain"

**Description:**
Align the project codebase with the official Raspberry Pi pi-gen build tool.

**Benefits:**
- Standard Raspberry Pi build process
- Easier to maintain
- Better community support
- Reproducible builds

**Our Implementation Plan:**
- [ ] Study pi-gen architecture
- [ ] Create PiMeet stage for pi-gen
- [ ] Migrate build scripts to pi-gen stages
- [ ] Test and validate
- [ ] Document build process

**Priority:** Phase 1 (P2 - Medium)

---

## Closed Issues (Reference)

### Issue #16: Microsoft Teams Integration
**Status:** Not Planned (Closed Jul 29, 2024)

**Original Request:** Add support for Microsoft Teams

**Our Status:** Being implemented in PRD-002 (Multi-Platform Support)
- Teams support is P0 priority
- Browser-based implementation
- Full feature parity target

---

### Issue #12: Documentation
**Status:** Completed (Closed Sep 24, 2022)

**Our Status:** Extended documentation created:
- docs/guides/user-guide.md
- docs/guides/administrator-guide.md
- docs/guides/deployment-guide.md
- docs/prd/*.md

---

### Issue #8: TV Standby on Shutdown
**Status:** Completed (Closed Sep 24, 2022)

**Our Status:** Implemented via HDMI-CEC in tv-lifecycle.service

---

### Issue #7: Extension Updates
**Status:** Completed (Closed Mar 6, 2022)

**Our Status:** update-extension.sh script available

---

## Fork Integration (xaghy/pimeet)

### Changes to Merge

#### 1. On-Pi Setup with Submodule
**Commit:** 3b12a6f (Aug 21, 2025)

**Description:**
Initial on-Pi setup functionality with submodule integration.

**Implementation Status:**
- [ ] Review implementation
- [ ] Assess compatibility
- [ ] Merge relevant components
- [ ] Test integration

#### 2. README Documentation Updates
**Commit:** b796ce3 (Aug 21, 2025)

**Description:**
Updates README for clarity and new setup process.

**Implementation Status:**
- [ ] Review changes
- [ ] Incorporate improvements
- [ ] Align with our documentation structure

---

## Contribution Guidelines

### For Upstream Contributions

When contributing back to pmansour/pimeet:

1. **Create focused PRs** - One feature/fix per PR
2. **Follow existing style** - Match project conventions
3. **Add tests** - If applicable
4. **Update documentation** - Include usage instructions
5. **Test thoroughly** - Verify on actual hardware

### PR Template
```markdown
## Description
[Brief description of changes]

## Related Issue
Fixes #XX

## Changes Made
- [List of changes]

## Testing Done
- [ ] Tested on Raspberry Pi 4B
- [ ] Verified with [platform]
- [ ] Documentation updated

## Screenshots
[If applicable]
```

---

## Upstream Communication

### Contact Information
- **Repository Issues:** https://github.com/pmansour/pimeet/issues
- **Help Group:** pimeet-help@googlegroups.com

### Planned Upstream Contributions

| Feature | Target PR | Timeline |
|---------|-----------|----------|
| Multi-platform provider architecture | TBD | After Phase 1 |
| Management agent | TBD | After Phase 1 |
| Security hardening | TBD | After Phase 2 |
| Docker support | TBD | After Phase 2 |

---

## Version History

| Date | Action | Details |
|------|--------|---------|
| 2025-12-15 | Initial creation | Documented all open PRs and issues |
