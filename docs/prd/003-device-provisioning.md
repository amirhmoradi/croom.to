# PRD-003: Zero-Touch Device Provisioning

## Document Information
| Field | Value |
|-------|-------|
| PRD ID | PRD-003 |
| Title | Zero-Touch Device Provisioning |
| Author | Engineering Team |
| Created | 2025-12-15 |
| Status | Draft |
| Priority | P1 - High |
| Target Phase | Phase 1 |

---

## 1. Overview

### 1.1 Problem Statement
Current PiMeet deployment requires:
1. Pre-imaging SD cards with credentials baked in
2. Technical expertise to run build scripts
3. Manual SSH access for configuration changes
4. No way to repurpose devices without reimaging

This approach doesn't scale for enterprise deployments of 50+ devices.

### 1.2 Solution
Implement zero-touch provisioning where:
- Generic PiMeet images can be flashed to SD cards
- Devices self-configure via web interface or management dashboard
- No technical expertise required for deployment
- Devices can be reassigned without reimaging

### 1.3 Success Metrics
- Device setup time < 10 minutes
- Non-technical staff can deploy devices
- Zero SSH required for normal operations
- Support fleet deployment of 100+ devices

---

## 2. Provisioning Methods

### 2.1 Method Comparison

| Method | Technical Skill | Network Required | Best For |
|--------|----------------|------------------|----------|
| Captive Portal | Low | WiFi available | Small deployments |
| USB Configuration | Low | No | Offline setup |
| Dashboard Push | Medium | Yes | Fleet management |
| QR Code Scan | Low | Yes | Quick setup |
| Auto-Discovery | Low | Yes | Enterprise LANs |

### 2.2 Supported Workflows

#### Workflow A: Captive Portal (Primary)
1. Flash generic PiMeet image to SD card
2. Boot device (connects to PiMeet-Setup WiFi AP)
3. Connect phone/laptop to PiMeet-Setup network
4. Browser auto-opens setup wizard
5. Configure WiFi, credentials, room name
6. Device reboots and connects to real network
7. Device registers with management dashboard

#### Workflow B: USB Configuration
1. Create config file on USB drive
2. Flash generic image and insert SD
3. Insert USB drive before boot
4. Device reads config from USB
5. Device configures itself
6. Remove USB, device operates normally

#### Workflow C: Dashboard Push
1. Pre-register device in dashboard (by MAC address)
2. Flash generic image with dashboard URL
3. Boot device on network
4. Device contacts dashboard for configuration
5. Dashboard pushes configuration
6. Device configures and starts operation

#### Workflow D: QR Code Setup
1. Boot device with generic image
2. Device displays QR code on TV
3. Scan QR with phone/tablet
4. Opens setup wizard in browser
5. Enter configuration
6. Device receives config via local connection

---

## 3. Features & Requirements

### 3.1 Generic Base Image (P0)

**User Story:** As an IT admin, I want to flash one image to all devices.

**Requirements:**
- [ ] Single image works for all deployments
- [ ] No credentials in base image
- [ ] Management dashboard URL configurable
- [ ] Automatic updates enabled
- [ ] First-boot setup mode detection

**Image Contents:**
- Raspberry Pi OS 64-bit
- PiMeet agent software
- Setup wizard web server
- Platform provider modules
- WiFi AP capabilities

### 3.2 Captive Portal Setup (P0)

**User Story:** As a facilities person, I want to set up a device without technical knowledge.

**Requirements:**
- [ ] Device creates WiFi access point on first boot
- [ ] Captive portal auto-opens on connection
- [ ] Mobile-friendly setup wizard
- [ ] WiFi network scanning and selection
- [ ] Credential input with validation
- [ ] Room naming and location
- [ ] Test connection before completing
- [ ] Progress indication during setup

**Setup Wizard Steps:**
1. Welcome screen with instructions
2. WiFi network selection
3. WiFi password entry
4. Account credentials (platform-specific)
5. Room configuration (name, location, timezone)
6. Dashboard registration (optional)
7. Test and verify
8. Setup complete / reboot

**Technical Implementation:**
- hostapd for WiFi AP
- dnsmasq for DHCP and DNS
- Flask/Express for setup web server
- NetworkManager for WiFi configuration

### 3.3 USB Configuration (P1)

**User Story:** As an IT admin, I want to pre-configure devices offline.

**Requirements:**
- [ ] Standard USB drive detection on boot
- [ ] JSON/YAML configuration file format
- [ ] Encrypted credential support
- [ ] Configuration validation
- [ ] Error reporting to USB drive
- [ ] Auto-eject after configuration

**Config File Format:**
```yaml
# pimeet-config.yaml
version: 1
device:
  name: "Conference Room A"
  location: "Building 1, Floor 2"
  timezone: "America/Los_Angeles"

network:
  wifi:
    ssid: "CorpWiFi"
    password: "encrypted:xxxxx"
  # or ethernet: true

meeting:
  platform: "google_meet"  # or teams, zoom, webex
  credentials:
    email: "room-a@company.com"
    password: "encrypted:xxxxx"

dashboard:
  url: "https://pimeet.company.com"
  enrollment_token: "xxxx-xxxx-xxxx"
```

### 3.4 Dashboard Auto-Registration (P1)

**User Story:** As an IT admin, I want devices to register automatically.

**Requirements:**
- [ ] Device contacts dashboard on first network connection
- [ ] Unique device identification (MAC, serial)
- [ ] Enrollment token validation
- [ ] Pending device queue in dashboard
- [ ] Admin approval workflow (optional)
- [ ] Automatic configuration push after approval

**Registration Flow:**
```
Device                          Dashboard
   │                               │
   │──────Registration Request────►│
   │   (MAC, serial, hostname)     │
   │                               │
   │◄─────Enrollment Token────────│
   │      Required                 │
   │                               │
   │──────Token + Device Info─────►│
   │                               │
   │◄─────Pending Approval────────│
   │      (or auto-approve)        │
   │                               │
   │◄─────Configuration Push──────│
   │                               │
   │──────Setup Complete──────────►│
   │                               │
```

### 3.5 QR Code Setup (P2)

**User Story:** As a user, I want to set up a device by scanning a QR code.

**Requirements:**
- [ ] Device generates unique QR code
- [ ] QR contains local connection info
- [ ] Mobile-friendly setup page
- [ ] Secure local communication
- [ ] Timeout after 10 minutes
- [ ] Regenerate QR option

**QR Code Contents:**
```json
{
  "type": "pimeet-setup",
  "device_id": "pi-xxxx",
  "local_ip": "192.168.4.1",
  "setup_url": "http://192.168.4.1:8080/setup",
  "expires": 1702656000
}
```

### 3.6 Network Configuration (P0)

**User Story:** As an IT admin, I want to configure WiFi or Ethernet.

**Requirements:**
- [ ] WiFi network scanning
- [ ] WPA2/WPA3 Enterprise support (802.1X)
- [ ] Hidden network support
- [ ] Static IP configuration
- [ ] Proxy configuration
- [ ] DNS settings
- [ ] Ethernet fallback

**Enterprise WiFi (802.1X):**
- EAP-TLS (certificate-based)
- EAP-PEAP (username/password)
- Certificate upload support
- CA certificate validation

### 3.7 Bulk Provisioning (P2)

**User Story:** As an IT admin, I want to provision many devices at once.

**Requirements:**
- [ ] CSV import of device configurations
- [ ] Batch USB drive preparation
- [ ] Pre-registration by MAC address
- [ ] Configuration templates
- [ ] Deployment tracking

**CSV Format:**
```csv
mac_address,device_name,location,wifi_ssid,wifi_password,platform,email,password
aa:bb:cc:dd:ee:ff,Room A,Building 1,CorpWiFi,secret,google_meet,room-a@co.com,pass123
```

---

## 4. Security Considerations

### 4.1 Credential Protection
- Credentials encrypted in transit (TLS)
- Credentials encrypted at rest (AES-256)
- No plaintext credentials in logs
- Secure credential input in wizard

### 4.2 Setup Mode Security
- Setup WiFi AP uses random password (displayed on screen)
- Setup mode times out after 30 minutes
- Setup mode disabled after successful configuration
- Re-enable requires physical button press

### 4.3 Enrollment Security
- Enrollment tokens single-use or time-limited
- Device verification (MAC address pre-registration)
- Admin approval option for unknown devices
- Audit logging of all enrollments

---

## 5. Technical Architecture

### 5.1 First Boot Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Boot Sequence                             │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Check Configuration │
                    │    /etc/pimeet/     │
                    └─────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
       Config Exists                     No Config
              │                                 │
              ▼                                 ▼
    ┌─────────────────┐              ┌─────────────────┐
    │  Normal Boot    │              │  Setup Mode     │
    │  Join Meetings  │              │  Start AP       │
    └─────────────────┘              │  Start Wizard   │
                                     └─────────────────┘
                                              │
              ┌───────────────────────────────┤
              │                               │
       USB Drive Present              No USB Drive
              │                               │
              ▼                               ▼
    ┌─────────────────┐              ┌─────────────────┐
    │  Read USB Config │              │  Display QR     │
    │  Apply Settings  │              │  Start Web UI   │
    └─────────────────┘              │  Wait for Setup │
              │                       └─────────────────┘
              ▼                               │
    ┌─────────────────┐                      │
    │  Reboot to      │                      │
    │  Normal Mode    │◄─────────────────────┘
    └─────────────────┘
```

### 5.2 Setup Wizard Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Setup Mode Services                          │
└─────────────────────────────────────────────────────────────────┘
                               │
    ┌──────────────────────────┼──────────────────────────┐
    │                          │                          │
    ▼                          ▼                          ▼
┌──────────┐            ┌──────────┐            ┌──────────┐
│ hostapd  │            │ dnsmasq  │            │  Setup   │
│ (WiFi AP)│            │ (DHCP/   │            │  Web     │
│          │            │  DNS)    │            │  Server  │
└──────────┘            └──────────┘            └──────────┘
     │                        │                       │
     │                        │                       │
     ▼                        ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NetworkManager                                │
│  - WiFi scanning                                                │
│  - Connection management                                        │
│  - Configuration persistence                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Configuration Storage

```
/etc/pimeet/
├── config.yaml          # Main configuration
├── credentials/         # Encrypted credentials
│   ├── google.enc
│   ├── microsoft.enc
│   └── zoom.enc
├── network/            # Network configuration
│   ├── wifi.conf
│   └── proxy.conf
├── certificates/       # 802.1X certificates
│   ├── ca.pem
│   └── client.pem
└── device.yaml         # Device identity
```

---

## 6. User Interface

### 6.1 Setup Wizard Screens

#### Screen 1: Welcome
```
┌─────────────────────────────────────────┐
│         Welcome to PiMeet Setup         │
│                                         │
│   This wizard will help you configure   │
│   your conference room device.          │
│                                         │
│   You'll need:                          │
│   • WiFi network name and password      │
│   • Meeting account credentials         │
│   • Room name                           │
│                                         │
│         [ Get Started → ]               │
└─────────────────────────────────────────┘
```

#### Screen 2: WiFi Selection
```
┌─────────────────────────────────────────┐
│         Select WiFi Network             │
│                                         │
│   ○ CorpWiFi        🔒 ████░░           │
│   ○ GuestNetwork    🔒 ███░░░           │
│   ○ OtherNetwork    🔒 ██░░░░           │
│                                         │
│   [ ] Use Ethernet instead              │
│   [ ] Connect to hidden network         │
│                                         │
│    [ ← Back ]        [ Next → ]         │
└─────────────────────────────────────────┘
```

#### Screen 3: WiFi Password
```
┌─────────────────────────────────────────┐
│      Enter WiFi Password                │
│                                         │
│   Network: CorpWiFi                     │
│                                         │
│   Password: [••••••••••••]  👁          │
│                                         │
│   [ ] Show password                     │
│   [ ] Save password                     │
│                                         │
│    [ ← Back ]        [ Connect → ]      │
└─────────────────────────────────────────┘
```

#### Screen 4: Account Setup
```
┌─────────────────────────────────────────┐
│      Meeting Account Setup              │
│                                         │
│   Platform: [ Google Meet ▼ ]           │
│                                         │
│   Email:    [room-a@company.com    ]    │
│   Password: [••••••••••••]  👁          │
│                                         │
│   [ ] Remember credentials              │
│                                         │
│    [ ← Back ]        [ Next → ]         │
└─────────────────────────────────────────┘
```

#### Screen 5: Room Configuration
```
┌─────────────────────────────────────────┐
│      Room Configuration                 │
│                                         │
│   Room Name:  [Conference Room A   ]    │
│   Location:   [Building 1, Floor 2 ]    │
│   Timezone:   [ America/Los_Angeles ▼ ] │
│                                         │
│   Management Dashboard (optional):      │
│   URL:        [https://pimeet.co.com]   │
│                                         │
│    [ ← Back ]        [ Finish → ]       │
└─────────────────────────────────────────┘
```

#### Screen 6: Setup Complete
```
┌─────────────────────────────────────────┐
│         Setup Complete! ✓               │
│                                         │
│   Your PiMeet device is configured.     │
│                                         │
│   Room: Conference Room A               │
│   Platform: Google Meet                 │
│   Account: room-a@company.com           │
│                                         │
│   The device will restart and begin     │
│   joining meetings automatically.       │
│                                         │
│         [ Restart Now ]                 │
└─────────────────────────────────────────┘
```

### 6.2 TV Display During Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                     PiMeet Setup Mode                           │
│                                                                 │
│                        ┌─────────┐                              │
│                        │ QR Code │                              │
│                        │  Here   │                              │
│                        └─────────┘                              │
│                                                                 │
│            Scan QR code with your phone to setup                │
│                                                                 │
│                           - OR -                                │
│                                                                 │
│            Connect to WiFi: PiMeet-Setup-A7B3                   │
│            Password: 847291                                     │
│                                                                 │
│            Setup will timeout in 28:45                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Implementation Plan

### Phase 1: Core Setup (3 weeks)
- Generic base image creation
- Captive portal WiFi AP
- Basic setup wizard
- WiFi configuration
- Credential storage

### Phase 2: Enhanced Setup (2 weeks)
- USB configuration support
- QR code setup
- Dashboard registration
- 802.1X enterprise WiFi

### Phase 3: Fleet Features (2 weeks)
- Bulk provisioning tools
- CSV import
- Configuration templates
- Deployment tracking

---

## 8. Testing Plan

### 8.1 Test Scenarios

| Scenario | Expected Result |
|----------|-----------------|
| First boot, no config | Enters setup mode |
| Setup via captive portal | Device configured, reboots |
| Setup via USB | Device configured, reboots |
| Setup via QR code | Device configured, reboots |
| Invalid WiFi password | Error shown, retry |
| Invalid credentials | Error shown, retry |
| Setup timeout | Returns to setup start |
| Dashboard registration | Device appears in dashboard |

### 8.2 Security Tests
- Credential encryption verification
- Setup mode timeout
- Token validation
- No credential leakage in logs

---

## 9. Success Criteria

- [ ] Non-technical user can set up device in < 10 minutes
- [ ] All provisioning methods working
- [ ] Devices register with dashboard automatically
- [ ] Zero SSH required for standard deployment
- [ ] Security audit passed
