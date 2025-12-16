# PRD-007: Modern Installation System

## Document Information
| Field | Value |
|-------|-------|
| PRD ID | PRD-007 |
| Title | Modern Installation & OS Compatibility |
| Author | Engineering Team |
| Created | 2025-12-15 |
| Status | Draft |
| Priority | P0 - Critical |
| Target Phase | Phase 1 |

---

## 1. Overview

### 1.1 Problem Statement
Current Croom installation requires:
- Pre-imaging SD cards with custom images
- Specific OS version (2022-09-22 Bullseye)
- Complete system replacement to install
- No upgrade path for existing installations
- Incompatible with latest Raspberry Pi OS

This approach is problematic because:
- Users may already have Raspberry Pi devices with existing setups
- IT departments prefer standard OS management
- Security updates require re-imaging
- No support for Raspberry Pi 5 or latest features
- Difficult to integrate with existing Pi deployments

### 1.2 Solution
Create a modern installation system that:
- Installs on any existing Raspberry Pi OS (Bookworm+)
- Uses standard package management (apt/deb)
- Supports non-destructive installation
- Provides one-line installer script
- Enables seamless updates
- Works alongside existing applications

### 1.3 Success Metrics
- Installation time < 10 minutes
- Works on fresh or existing Raspberry Pi OS
- Zero data loss during installation
- Update deployment < 2 minutes
- Support for OS upgrades (Bookworm → Trixie)

---

## 2. Supported Platforms

### 2.1 Hardware Support

| Hardware | Status | Notes |
|----------|--------|-------|
| Raspberry Pi 5 (4GB/8GB) | Primary | Best performance |
| Raspberry Pi 4B (4GB/8GB) | Primary | Widely deployed |
| Raspberry Pi 4B (2GB) | Secondary | Limited AI features |
| Raspberry Pi 400 | Secondary | Keyboard form factor |
| Raspberry Pi 3B+ | Limited | No AI, basic features |

### 2.2 Operating System Support

| OS Version | Based On | Status | Notes |
|------------|----------|--------|-------|
| Raspberry Pi OS Bookworm (64-bit) | Debian 12 | Primary | Current stable |
| Raspberry Pi OS Trixie (64-bit) | Debian 13 | Planned | Coming 2025 |
| Raspberry Pi OS Bookworm (32-bit) | Debian 12 | Limited | Pi 3/Zero 2 only |
| Ubuntu 24.04 (arm64) | Ubuntu | Secondary | Server deployments |
| Debian 12+ (arm64) | Debian | Secondary | Advanced users |

**Minimum Requirements:**
- Raspberry Pi OS Bookworm or newer
- 64-bit recommended (required for AI features)
- 2GB+ RAM (4GB+ for AI features)
- 16GB+ storage (32GB+ recommended)
- Network connectivity

### 2.3 Desktop Environment Support

| Environment | Support | Notes |
|-------------|---------|-------|
| Raspberry Pi Desktop (Wayland) | Full | Default on Pi 4/5 |
| Raspberry Pi Desktop (X11) | Full | Fallback/Pi 3 |
| Headless (no desktop) | Partial | Dashboard-managed only |
| LXDE | Full | Legacy option |

---

## 3. Installation Methods

### 3.1 One-Line Installer (Primary)

**User Story:** As a user, I want to install Croom with a single command.

```bash
curl -fsSL https://get.croom.io | bash
```

**Installer Flow:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    Croom Installer                              │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Check Prerequisites │
                    │ - OS version        │
                    │ - Architecture      │
                    │ - Free space        │
                    │ - Network           │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Add Croom Repo     │
                    │ - GPG key           │
                    │ - APT source        │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Install Packages    │
                    │ - croom-core       │
                    │ - croom-ui         │
                    │ - croom-ai (opt)   │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Initial Setup       │
                    │ - Create config     │
                    │ - Enable services   │
                    │ - Setup wizard      │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Launch Setup UI     │
                    │ (or print URL)      │
                    └─────────────────────┘
```

**Interactive Mode:**
```bash
# Interactive with prompts
curl -fsSL https://get.croom.io | bash

# Non-interactive with defaults
curl -fsSL https://get.croom.io | bash -s -- --non-interactive

# Specify options
curl -fsSL https://get.croom.io | bash -s -- \
  --with-ai \
  --dashboard-url https://croom.company.com \
  --room-name "Conference Room A"
```

### 3.2 APT Package Installation

**User Story:** As an IT admin, I want to install via standard package management.

```bash
# Add repository
curl -fsSL https://repo.croom.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/croom.gpg
echo "deb [signed-by=/usr/share/keyrings/croom.gpg] https://repo.croom.io/apt stable main" | \
  sudo tee /etc/apt/sources.list.d/croom.list

# Install
sudo apt update
sudo apt install croom

# Optional packages
sudo apt install croom-ai        # AI features
sudo apt install croom-ui        # Touch screen UI
sudo apt install croom-dev       # Development tools
```

### 3.3 Snap Package (Alternative)

```bash
sudo snap install croom
```

**Pros:**
- Automatic updates
- Sandboxed
- Single package

**Cons:**
- Larger size
- Potential permission issues
- Snap infrastructure required

### 3.4 Manual/Offline Installation

For air-gapped environments:

```bash
# Download packages
wget https://repo.croom.io/packages/croom_2.0.0_arm64.deb
wget https://repo.croom.io/packages/croom-ai_2.0.0_arm64.deb

# Install
sudo dpkg -i croom_2.0.0_arm64.deb croom-ai_2.0.0_arm64.deb
sudo apt-get install -f  # Install dependencies
```

---

## 4. Package Architecture

### 4.1 Package Structure

```
croom (metapackage)
├── croom-core           # Core agent and meeting functionality
│   ├── /usr/bin/croom-agent
│   ├── /usr/bin/croom-cli
│   ├── /usr/lib/croom/
│   ├── /etc/croom/
│   └── /lib/systemd/system/croom-agent.service
│
├── croom-browser        # Chromium configuration and extensions
│   ├── /usr/lib/croom/browser/
│   ├── /usr/lib/croom/extensions/
│   └── /lib/systemd/system/croom-browser.service
│
├── croom-ui             # Touch screen UI
│   ├── /usr/bin/croom-ui
│   ├── /usr/lib/croom/ui/
│   └── /lib/systemd/system/croom-ui.service
│
├── croom-ai             # AI features and models
│   ├── /usr/lib/croom/ai/
│   ├── /usr/share/croom/models/
│   └── /lib/systemd/system/croom-ai.service
│
└── croom-dev            # Development and debugging tools
    ├── /usr/bin/croom-debug
    └── /usr/share/croom/examples/
```

### 4.2 Dependencies

**croom-core:**
```
Depends: python3 (>= 3.11),
         python3-pip,
         chromium-browser | chromium,
         pulseaudio | pipewire-pulse,
         libcec6,
         network-manager
Recommends: croom-browser
```

**croom-ai:**
```
Depends: croom-core,
         python3-numpy,
         python3-opencv
Recommends: hailo-all | libedgetpu1-std
Suggests: croom-models-full
```

**croom-ui:**
```
Depends: croom-core,
         python3-pyside6,
         qml6-module-qtquick
```

### 4.3 Configuration File Locations

| File | Purpose | Managed By |
|------|---------|------------|
| `/etc/croom/config.yaml` | Main configuration | Admin/Installer |
| `/etc/croom/credentials/` | Encrypted credentials | Agent |
| `/var/lib/croom/` | Runtime data | Agent |
| `/var/log/croom/` | Log files | Agent |
| `~/.config/croom/` | User preferences | UI |

---

## 5. Installation Requirements

### 5.1 Pre-Installation Checks

```python
class PreInstallChecker:
    MIN_OS_VERSION = "bookworm"
    MIN_PYTHON = "3.11"
    MIN_DISK_SPACE_MB = 500
    MIN_RAM_MB = 1024

    def check_all(self):
        checks = [
            self.check_os_version(),
            self.check_architecture(),
            self.check_disk_space(),
            self.check_memory(),
            self.check_network(),
            self.check_existing_install()
        ]
        return all(checks)

    def check_os_version(self):
        # Must be Bookworm or newer
        pass

    def check_architecture(self):
        # Warn if 32-bit, some features unavailable
        pass
```

### 5.2 System Modifications

**Services Installed:**
| Service | Purpose | Auto-start |
|---------|---------|------------|
| croom-agent | Core agent | Yes |
| croom-browser | Meeting browser | Yes |
| croom-ui | Touch interface | Optional |
| croom-ai | AI processing | Optional |

**System Changes:**
- Adds Croom user group
- Configures auto-login (optional)
- Sets up audio devices
- Enables required GPIO/I2C (if needed)
- Adds desktop autostart entries

### 5.3 Permissions

```
# /etc/polkit-1/rules.d/50-croom.rules
polkit.addRule(function(action, subject) {
    if (subject.user == "croom" &&
        action.id.indexOf("org.freedesktop.NetworkManager") == 0) {
        return polkit.Result.YES;
    }
});
```

---

## 6. Update System

### 6.1 Update Methods

**APT Updates (Standard):**
```bash
sudo apt update && sudo apt upgrade croom
```

**Automatic Updates:**
```yaml
# /etc/croom/config.yaml
updates:
  auto_check: true
  auto_install: false  # or true for automatic
  check_interval: 86400  # daily
  notify: true
```

**Dashboard-Initiated Updates:**
- Dashboard can trigger updates
- Staged rollouts
- Rollback capability

### 6.2 Update Process

```
┌─────────────────────────────────────────────────────────────────┐
│                    Update Process                                │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Check for Updates   │
                    │ (APT or Dashboard)  │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Download Packages   │
                    │ (Background)        │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Wait for Idle       │
                    │ (No active meeting) │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Backup Config       │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Install Updates     │
                    │ (dpkg/apt)          │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Restart Services    │
                    │ (systemctl)         │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Verify & Report     │
                    └─────────────────────┘
```

### 6.3 Rollback Support

```bash
# Manual rollback
sudo apt install croom=1.9.0

# Automatic rollback on failure
# Agent detects post-update failures and reverts
```

### 6.4 Version Channels

| Channel | Purpose | Update Frequency |
|---------|---------|------------------|
| stable | Production | Monthly |
| beta | Testing | Weekly |
| nightly | Development | Daily |

---

## 7. OS Upgrade Support

### 7.1 Bookworm → Trixie Migration

Croom should survive OS upgrades:

```bash
# Standard Debian upgrade process
sudo apt update && sudo apt full-upgrade
sudo sed -i 's/bookworm/trixie/g' /etc/apt/sources.list.d/*
sudo apt update && sudo apt full-upgrade
```

**Post-Upgrade:**
- Croom packages rebuilt for Trixie
- Automatic compatibility adjustments
- Config preserved

### 7.2 Compatibility Layer

```python
class OSCompatibility:
    def __init__(self):
        self.os_release = self._read_os_release()
        self.codename = self.os_release.get('VERSION_CODENAME')

    def get_audio_system(self):
        # Bookworm: PipeWire or PulseAudio
        # Trixie: PipeWire default
        if self.codename >= 'trixie':
            return 'pipewire'
        return self._detect_audio_system()

    def get_display_server(self):
        # Bookworm: Wayland on Pi 4/5, X11 on Pi 3
        # Trixie: Wayland everywhere
        return os.environ.get('XDG_SESSION_TYPE', 'x11')
```

---

## 8. Uninstallation

### 8.1 Clean Removal

```bash
# Remove Croom but keep config
sudo apt remove croom

# Complete removal including config
sudo apt purge croom
sudo rm -rf /etc/croom /var/lib/croom /var/log/croom
```

### 8.2 Uninstaller Script

```bash
curl -fsSL https://get.croom.io/uninstall | bash
```

**Uninstaller Actions:**
- Stop and disable services
- Remove packages
- Optionally remove config and data
- Restore system settings (auto-login, etc.)
- Remove desktop entries

---

## 9. Migration from Legacy

### 9.1 From Pre-Imaged Installation

For users with existing Croom (old image-based):

```bash
# Migration script
curl -fsSL https://get.croom.io/migrate | bash
```

**Migration Process:**
1. Detect existing installation
2. Backup current config and credentials
3. Stop legacy services
4. Install new packages
5. Migrate configuration
6. Start new services
7. Remove legacy components (optional)

### 9.2 Configuration Migration

```python
class ConfigMigrator:
    def migrate(self, legacy_path, new_path):
        # Read legacy config (various formats)
        legacy = self._read_legacy_config(legacy_path)

        # Transform to new format
        new_config = {
            'version': 2,
            'room': {
                'name': legacy.get('hostname', 'Croom'),
                'location': legacy.get('location', '')
            },
            'meeting': {
                'platform': 'auto',
                'credentials': self._migrate_credentials(legacy)
            },
            # ... more fields
        }

        self._write_config(new_path, new_config)
```

---

## 10. Testing Plan

### 10.1 Installation Matrix

| OS | Pi Model | Install Method | Status |
|----|----------|----------------|--------|
| Bookworm 64-bit | Pi 5 | curl installer | Test |
| Bookworm 64-bit | Pi 4 | curl installer | Test |
| Bookworm 64-bit | Pi 5 | apt | Test |
| Bookworm 64-bit | Pi 4 | apt | Test |
| Bookworm 32-bit | Pi 3B+ | curl installer | Test |
| Ubuntu 24.04 | Pi 5 | apt | Test |
| Fresh install | All | curl installer | Test |
| Existing system | All | curl installer | Test |

### 10.2 Upgrade Testing

- [ ] Update from previous version
- [ ] Update with active meeting (should wait)
- [ ] Rollback on failure
- [ ] Config preservation
- [ ] OS upgrade survival

### 10.3 Uninstall Testing

- [ ] Clean removal
- [ ] Complete purge
- [ ] No orphaned files/services
- [ ] System returns to clean state

---

## 11. Implementation Plan

### Sprint 1: Package Infrastructure (Week 1-2)
- [ ] Create Debian package structure
- [ ] Set up package repository
- [ ] GPG key management
- [ ] Basic croom-core package

### Sprint 2: Installer Script (Week 3-4)
- [ ] Pre-install checks
- [ ] Repository setup
- [ ] Package installation
- [ ] Initial configuration
- [ ] Post-install setup

### Sprint 3: Services & Integration (Week 5-6)
- [ ] Systemd service files
- [ ] Auto-start configuration
- [ ] Desktop integration
- [ ] Permission setup

### Sprint 4: Update & Migration (Week 7-8)
- [ ] Update system
- [ ] Rollback support
- [ ] Legacy migration
- [ ] Documentation

---

## 12. Open Questions

1. Should we support Raspberry Pi 3B+ or focus on Pi 4/5 only?
2. Snap vs APT as primary distribution method?
3. Should auto-login be configured by default?
4. How to handle systems with existing Chromium configuration?
5. Should we support Ubuntu Server (headless) deployments?

---

## 13. Success Criteria

- [ ] Installation works on fresh Bookworm
- [ ] Installation works on existing system (no data loss)
- [ ] All packages installable via apt
- [ ] One-line installer working
- [ ] Updates preserve configuration
- [ ] Legacy migration functional
- [ ] Uninstall leaves clean system

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-15 | Claude | Initial PRD |
