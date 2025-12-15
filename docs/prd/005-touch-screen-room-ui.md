# PRD-005: Touch Screen Room Management UI

## Document Information
| Field | Value |
|-------|-------|
| PRD ID | PRD-005 |
| Title | Touch Screen Room Management UI |
| Author | Engineering Team |
| Created | 2025-12-15 |
| Status | Draft |
| Priority | P1 - High |
| Target Phase | Phase 1.5 |

---

## 1. Overview

### 1.1 Problem Statement
Currently, PiMeet devices require:
- SSH access for configuration changes
- Central dashboard for management (requires network/internet)
- No local interface for room administrators or users
- No way to troubleshoot or configure without technical knowledge

Room administrators and users need a local interface to:
- Manage room settings without IT involvement
- Join ad-hoc meetings quickly
- Troubleshoot basic issues
- View room status and upcoming meetings

### 1.2 Solution
Build a touch-optimized local management UI that runs directly on the Raspberry Pi, accessible via:
- Official Raspberry Pi Touch Display (7")
- Third-party HDMI touch displays (various sizes)
- Main TV display with IR remote/USB keyboard navigation

### 1.3 Success Metrics
- Room setup completable in < 5 minutes via touch UI
- 90% of common tasks achievable without IT support
- User satisfaction rating > 4/5
- Reduce IT support tickets by 50%

---

## 2. Supported Hardware

### 2.1 Touch Displays

| Display | Size | Resolution | Interface | Priority |
|---------|------|------------|-----------|----------|
| Raspberry Pi Touch Display | 7" | 800x480 | DSI | P0 |
| Raspberry Pi Touch Display 2 | 7" | 720x1280 | DSI | P0 |
| Generic HDMI Touch | 5-10" | Various | HDMI+USB | P1 |
| Waveshare Displays | 3.5-10" | Various | SPI/HDMI | P2 |

### 2.2 Alternative Input Methods

For rooms without touch displays:
| Input | Use Case | Implementation |
|-------|----------|----------------|
| IR Remote | TV-based navigation | D-pad + OK navigation |
| USB Keyboard | Admin access | Full keyboard support |
| USB Mouse | Click navigation | Standard pointer |
| Web Interface | Local network access | Browser-based same UI |

### 2.3 Display Modes

```
┌─────────────────────────────────────────────────────────────────┐
│                    Display Configuration                         │
└─────────────────────────────────────────────────────────────────┘

Mode 1: Touch Display Only (Small Rooms)
┌─────────────────┐
│   7" Touch      │  ← Full UI on touch display
│   Display       │  ← TV used for meetings only
└─────────────────┘

Mode 2: Touch Display + TV (Conference Rooms)
┌─────────────────┐     ┌─────────────────────────┐
│   7" Touch      │     │         TV              │
│   (Control)     │     │    (Meeting/Status)     │
└─────────────────┘     └─────────────────────────┘

Mode 3: TV Only with Remote (Simple Rooms)
┌─────────────────────────────────────────┐
│              TV Display                  │
│    (Meetings + On-Screen UI/Remote)     │
└─────────────────────────────────────────┘
```

---

## 3. User Interface Design

### 3.1 Design Principles

1. **Touch-First:** Large touch targets (minimum 44x44px)
2. **Glanceable:** Key info visible from across the room
3. **Simple Navigation:** Maximum 2 taps to any function
4. **Accessible:** High contrast, large fonts, screen reader support
5. **Multi-language:** Internationalization ready

### 3.2 UI Framework Selection

| Framework | Pros | Cons | Decision |
|-----------|------|------|----------|
| **Qt/QML** | Native performance, touch optimized | C++ complexity | Selected |
| PyQt/PySide | Python, good Qt bindings | Slightly slower | Alternative |
| Electron | Web tech, easy development | Heavy, slow on Pi | Not selected |
| Flutter | Beautiful UI, cross-platform | Resource heavy | Future consideration |
| GTK4 | Native Linux, lightweight | Less touch-friendly | Not selected |

**Selected:** Qt6/QML with Python bindings (PySide6) for balance of performance and development speed.

### 3.3 Screen Layouts

#### 3.3.1 Home Screen (Idle State)
```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────┐                                              10:30 AM  │
│  │LOGO │   Conference Room A                          ● Online  │
│  └─────┘                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│              ┌─────────────────────────────────┐                │
│              │                                 │                │
│              │     Next Meeting: 11:00 AM      │                │
│              │     "Weekly Standup"            │                │
│              │     Google Meet                 │                │
│              │                                 │                │
│              │     Starting in 30 minutes      │                │
│              │                                 │                │
│              └─────────────────────────────────┘                │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │              │  │              │  │              │          │
│  │  Join Now    │  │  Quick Meet  │  │   Settings   │          │
│  │              │  │              │  │      ⚙       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  📅 3 meetings today    🌡 42°C    📶 Strong    🔋 Powered      │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.3.2 In-Meeting Screen
```
┌─────────────────────────────────────────────────────────────────┐
│  ● LIVE   Weekly Standup (Google Meet)           45:23 elapsed │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                   Meeting in progress on TV                     │
│                                                                 │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐│
│  │            │  │            │  │            │  │            ││
│  │    🎤      │  │    📷      │  │    🖥      │  │    📞      ││
│  │   Mute     │  │   Camera   │  │   Share    │  │   Leave    ││
│  │            │  │            │  │            │  │            ││
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Participants: 8     │  Quality: Good ████░░  │  Recording  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  🔊 Volume: ████████░░░░░░░░░░░░░░    [  -  ] [  +  ]          │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.3.3 Settings Screen
```
┌─────────────────────────────────────────────────────────────────┐
│  ←  Settings                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  🏠  Room Settings                                      >   ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │  📶  Network                                            >   ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │  🔊  Audio & Video                                      >   ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │  📅  Calendar & Accounts                                >   ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │  🤖  AI Features                                        >   ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │  🔒  Admin Settings                          🔐 Locked  >   ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │  ℹ️  About & Diagnostics                                >   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.3.4 Quick Join Screen
```
┌─────────────────────────────────────────────────────────────────┐
│  ←  Join a Meeting                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Enter meeting code or link:                                ││
│  │  ┌─────────────────────────────────────────────────────┐   ││
│  │  │  abc-defg-hij                                       │   ││
│  │  └─────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Platform:  ○ Auto-detect  ● Google Meet  ○ Teams  ○ Zoom      │
│                                                                 │
│              ┌─────────────────────────────────┐                │
│              │                                 │                │
│              │         Join Meeting            │                │
│              │                                 │                │
│              └─────────────────────────────────┘                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Recent Meetings:                                           ││
│  │  • abc-defg-hij (Google Meet) - 2 hours ago                 ││
│  │  • Team Sync (Teams) - Yesterday                            ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  [ 1 ] [ 2 ] [ 3 ] [ 4 ] [ 5 ] [ 6 ] [ 7 ] [ 8 ] [ 9 ] [ 0 ]   │
│  [ Q ] [ W ] [ E ] [ R ] [ T ] [ Y ] [ U ] [ I ] [ O ] [ P ]   │
│                        ...                                      │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.3.5 Diagnostics Screen
```
┌─────────────────────────────────────────────────────────────────┐
│  ←  Diagnostics                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  System Status                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  CPU:         ████░░░░░░  38%     Temperature: 45°C        ││
│  │  Memory:      ██████░░░░  62%     Disk: 12.4 GB free       ││
│  │  Network:     ● Connected (192.168.1.105)                  ││
│  │  Dashboard:   ● Connected                                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Devices                                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  📷 Camera:    ● Logitech C920 (Working)      [ Test ]     ││
│  │  🎤 Mic:       ● Logitech C920 (Working)      [ Test ]     ││
│  │  🔊 Speaker:   ● HDMI Audio (Working)         [ Test ]     ││
│  │  📺 Display:   ● HDMI-1 (1920x1080)                        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  View Logs   │  │  Run Tests   │  │   Restart    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  Version: 2.1.0   |   Agent: Online   |   Last update: 2h ago  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Features & Requirements

### 4.1 Home & Status (P0)

**User Story:** As a room user, I want to see room status at a glance.

**Requirements:**
- [ ] Room name and status prominently displayed
- [ ] Current time with timezone
- [ ] Next meeting with countdown
- [ ] Network and system health indicators
- [ ] Quick action buttons (Join, Settings)
- [ ] Calendar view of today's meetings

### 4.2 Meeting Controls (P0)

**User Story:** As a meeting participant, I want to control the meeting from the touch screen.

**Requirements:**
- [ ] Mute/unmute microphone
- [ ] Enable/disable camera
- [ ] Leave meeting
- [ ] Adjust volume
- [ ] View participant count
- [ ] Screen share trigger (if supported)
- [ ] Meeting duration display
- [ ] Quality indicator

### 4.3 Quick Join (P0)

**User Story:** As a room user, I want to join ad-hoc meetings quickly.

**Requirements:**
- [ ] Enter meeting code/link
- [ ] On-screen keyboard (touch optimized)
- [ ] Auto-detect meeting platform
- [ ] Recent meetings list
- [ ] QR code scanner (if camera available)
- [ ] Copy/paste from clipboard

### 4.4 Room Settings (P1)

**User Story:** As a room administrator, I want to configure basic settings locally.

**Requirements:**
- [ ] Room name and location
- [ ] Timezone selection
- [ ] Display brightness/timeout
- [ ] Default audio/video settings
- [ ] Language selection
- [ ] Theme (light/dark/auto)

### 4.5 Network Configuration (P1)

**User Story:** As an IT admin, I want to configure network settings locally.

**Requirements:**
- [ ] View current network status
- [ ] Connect to WiFi networks
- [ ] WiFi network scanning
- [ ] Static IP configuration
- [ ] Proxy settings
- [ ] Network diagnostics (ping, DNS)

### 4.6 Audio/Video Settings (P1)

**User Story:** As a room user, I want to configure audio/video devices.

**Requirements:**
- [ ] Select audio input (microphone)
- [ ] Select audio output (speakers)
- [ ] Select camera
- [ ] Test audio (play test tone)
- [ ] Test microphone (record and playback)
- [ ] Test camera (preview)
- [ ] Volume levels

### 4.7 Calendar & Accounts (P1)

**User Story:** As an admin, I want to manage meeting accounts locally.

**Requirements:**
- [ ] View connected accounts
- [ ] Add/remove meeting accounts
- [ ] OAuth flow for authentication
- [ ] Calendar sync status
- [ ] Manual calendar refresh

### 4.8 AI Features Toggle (P2)

**User Story:** As a room user, I want to control AI features.

**Requirements:**
- [ ] Enable/disable speaker tracking
- [ ] Enable/disable auto-framing
- [ ] Enable/disable noise reduction
- [ ] Enable/disable occupancy detection
- [ ] Privacy mode toggle

### 4.9 Admin Settings (P1)

**User Story:** As an IT admin, I want to access advanced settings with authentication.

**Requirements:**
- [ ] PIN/password protection
- [ ] Factory reset option
- [ ] Dashboard connection settings
- [ ] Software update controls
- [ ] Debug mode toggle
- [ ] Export logs
- [ ] SSH enable/disable

### 4.10 Diagnostics (P1)

**User Story:** As an IT admin, I want to troubleshoot issues locally.

**Requirements:**
- [ ] System resource usage
- [ ] Network connectivity tests
- [ ] Device status (camera, mic, speakers)
- [ ] View recent logs
- [ ] Run automated diagnostics
- [ ] Generate diagnostic report
- [ ] Restart services

---

## 5. Technical Architecture

### 5.1 Application Structure

```
pimeet-ui/
├── main.py                 # Application entry point
├── qml/
│   ├── main.qml           # Root QML file
│   ├── components/        # Reusable components
│   │   ├── Button.qml
│   │   ├── Card.qml
│   │   ├── StatusBar.qml
│   │   └── ...
│   ├── screens/           # Screen definitions
│   │   ├── HomeScreen.qml
│   │   ├── MeetingScreen.qml
│   │   ├── SettingsScreen.qml
│   │   ├── QuickJoinScreen.qml
│   │   └── DiagnosticsScreen.qml
│   └── themes/            # Theme definitions
│       ├── Light.qml
│       └── Dark.qml
├── src/
│   ├── __init__.py
│   ├── app.py             # Application logic
│   ├── config.py          # Configuration management
│   ├── meeting.py         # Meeting control interface
│   ├── system.py          # System information
│   ├── network.py         # Network management
│   └── dbus_interface.py  # D-Bus for system integration
├── assets/
│   ├── icons/
│   ├── fonts/
│   └── images/
└── pimeet-ui.service      # systemd service file
```

### 5.2 Integration with Agent

```
┌─────────────────────────────────────────────────────────────────┐
│                      Touch Screen UI                             │
│                      (PySide6/QML)                              │
└─────────────────────────────────────────────────────────────────┘
                               │
                          D-Bus / IPC
                               │
┌─────────────────────────────────────────────────────────────────┐
│                      PiMeet Agent                                │
│   (Meeting control, config, metrics, dashboard connection)      │
└─────────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│    Chromium      │ │    System        │ │    Dashboard     │
│   (Meetings)     │ │  (NetworkManager │ │   (Remote Mgmt)  │
│                  │ │   PulseAudio)    │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### 5.3 D-Bus Interface

```python
# Agent exposes D-Bus interface for UI
interface com.pimeet.Agent {
    # Properties
    property string Status;
    property string MeetingState;
    property dict SystemMetrics;

    # Methods
    method JoinMeeting(string code, string platform);
    method LeaveMeeting();
    method MuteAudio(bool mute);
    method MuteVideo(bool mute);
    method GetConfig() -> dict;
    method SetConfig(dict config);
    method GetCalendarEvents() -> array;
    method RunDiagnostics() -> dict;

    # Signals
    signal MeetingStateChanged(string state);
    signal AlertTriggered(string alert);
    signal ConfigChanged(dict config);
}
```

### 5.4 Local Web Interface

For network access without touch:
- Same UI served via local web server
- Accessible at `http://pimeet.local:8080` or `http://<ip>:8080`
- WebSocket for real-time updates
- Responsive design for various screen sizes

---

## 6. Accessibility

### 6.1 Requirements

- [ ] High contrast mode
- [ ] Large text mode
- [ ] Screen reader support (Qt Accessibility)
- [ ] Keyboard navigation for all functions
- [ ] Focus indicators
- [ ] Color-blind friendly palette

### 6.2 Touch Targets

- Minimum touch target: 44x44 pixels (10mm at typical PPI)
- Spacing between targets: minimum 8 pixels
- Important actions: 60x60 pixels or larger

---

## 7. Security

### 7.1 Access Control

| Area | Default Access | Admin Override |
|------|----------------|----------------|
| Meeting controls | Open | N/A |
| Quick join | Open | Can disable |
| Room settings | Open | Can lock |
| Network settings | PIN required | N/A |
| Account settings | PIN required | N/A |
| Admin settings | PIN required | N/A |

### 7.2 PIN Protection

- 4-8 digit PIN
- Lockout after 5 failed attempts (5 minutes)
- PIN set during initial setup
- Reset via dashboard or physical button combo

---

## 8. Implementation Plan

### Sprint 1: Core UI (Week 1-2)
- [ ] Qt/QML project setup
- [ ] Theme system
- [ ] Home screen
- [ ] Status bar component
- [ ] Navigation framework

### Sprint 2: Meeting Features (Week 3-4)
- [ ] Meeting controls screen
- [ ] Quick join screen
- [ ] On-screen keyboard
- [ ] D-Bus integration with agent

### Sprint 3: Settings (Week 5-6)
- [ ] Settings screens
- [ ] Network configuration UI
- [ ] Audio/video settings
- [ ] Admin PIN protection

### Sprint 4: Polish (Week 7-8)
- [ ] Diagnostics screen
- [ ] Local web interface
- [ ] Accessibility improvements
- [ ] Testing on hardware
- [ ] Documentation

---

## 9. Hardware Testing Matrix

| Device | Display | Touch | Status |
|--------|---------|-------|--------|
| Pi 4 + Official 7" | DSI | Yes | Primary target |
| Pi 5 + Official 7" | DSI | Yes | Primary target |
| Pi 4 + HDMI 5" | HDMI | Yes | Secondary |
| Pi 4 + TV only | HDMI | No (remote) | Secondary |

---

## 10. Open Questions

1. Should the touch UI be mandatory or optional component?
2. What is the minimum supported display resolution?
3. Should we support portrait orientation for wall-mounted displays?
4. What languages should be supported at launch?
5. Should the local web interface be enabled by default?

---

## 11. Success Criteria

- [ ] UI runs at 60fps on Raspberry Pi 4
- [ ] All core features accessible via touch
- [ ] Keyboard/remote navigation complete
- [ ] Local web interface functional
- [ ] Accessibility audit passed
- [ ] User testing feedback positive

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-15 | Claude | Initial PRD |
