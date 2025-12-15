# PRD-002: Multi-Platform Meeting Support

## Document Information
| Field | Value |
|-------|-------|
| PRD ID | PRD-002 |
| Title | Multi-Platform Meeting Support |
| Author | Engineering Team |
| Created | 2025-12-15 |
| Status | Draft |
| Priority | P0 - Critical |
| Target Phase | Phase 1 |

---

## 1. Overview

### 1.1 Problem Statement
PiMeet currently only supports Google Meet, limiting its adoption in enterprises that use:
- Microsoft Teams (dominant in enterprise)
- Zoom (popular for external meetings)
- Webex (Cisco shops)
- Other platforms

Organizations often use multiple platforms, requiring rooms to support all of them.

### 1.2 Solution
Implement a modular meeting platform architecture that allows PiMeet to join meetings on any major video conferencing platform automatically.

### 1.3 Success Metrics
- Support at least 4 major platforms (Google Meet, Teams, Zoom, Webex)
- Automatic platform detection from calendar events
- < 30 second meeting join time
- 99% successful join rate

---

## 2. Supported Platforms

### 2.1 Priority Matrix

| Platform | Market Share | Priority | Implementation |
|----------|-------------|----------|----------------|
| Google Meet | 25% | P0 (Current) | Chrome Extension |
| Microsoft Teams | 40% | P0 | Browser-based |
| Zoom | 30% | P1 | Browser-based |
| Webex | 5% | P2 | Browser-based |
| BlueJeans | <5% | P3 | Browser-based |

### 2.2 Platform-Specific Requirements

#### Google Meet (Current)
- Status: Implemented via Minimeet extension
- Enhancements needed:
  - [ ] Better error handling
  - [ ] Meeting quality reporting
  - [ ] Lobby handling improvements

#### Microsoft Teams
- Join via browser (teams.microsoft.com)
- Requirements:
  - [ ] Microsoft account authentication
  - [ ] Guest join support
  - [ ] Lobby bypass for organization accounts
  - [ ] Teams-specific controls (raise hand, reactions)
  - [ ] Teams meeting settings (camera, mic defaults)

#### Zoom
- Join via browser (zoom.us/wc)
- Requirements:
  - [ ] Zoom account authentication
  - [ ] Meeting ID/password handling
  - [ ] Waiting room support
  - [ ] Zoom-specific controls
  - [ ] Web client feature parity

#### Webex
- Join via browser (webex.com)
- Requirements:
  - [ ] Webex account authentication
  - [ ] Personal room support
  - [ ] Meeting number/password
  - [ ] Lobby handling

---

## 3. Architecture

### 3.1 Modular Platform Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Meeting Orchestrator                          │
│  - Calendar Integration                                         │
│  - Platform Detection                                           │
│  - Meeting State Management                                     │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Platform Router                               │
│  - URL Pattern Matching                                         │
│  - Platform Selection                                           │
│  - Fallback Handling                                            │
└─────────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   Google Meet    │ │ Microsoft Teams  │ │      Zoom        │
│    Provider      │ │    Provider      │ │    Provider      │
└──────────────────┘ └──────────────────┘ └──────────────────┘
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Chrome Browser                                │
│  - Hardware Acceleration                                        │
│  - Audio/Video Devices                                          │
│  - Extension Management                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Platform Provider Interface

Each platform implements a common interface:

```typescript
interface MeetingPlatformProvider {
  // Platform identification
  name: string;
  urlPatterns: RegExp[];

  // Authentication
  authenticate(credentials: Credentials): Promise<AuthResult>;
  isAuthenticated(): boolean;

  // Meeting lifecycle
  joinMeeting(meetingInfo: MeetingInfo): Promise<JoinResult>;
  leaveMeeting(): Promise<void>;

  // Meeting controls
  muteAudio(): void;
  unmuteAudio(): void;
  muteVideo(): void;
  unmuteVideo(): void;

  // Status
  getMeetingStatus(): MeetingStatus;
  getParticipantCount(): number;

  // Events
  onMeetingStarted: Event;
  onMeetingEnded: Event;
  onError: Event;
}
```

### 3.3 Calendar Integration

Support multiple calendar sources:

```
┌─────────────────────────────────────────────────────────────────┐
│                   Calendar Aggregator                            │
└─────────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Google Calendar  │ │  Microsoft 365   │ │   Exchange/EWS   │
│      API         │ │   Graph API      │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## 4. Features & Requirements

### 4.1 Platform Detection (P0)

**User Story:** As a PiMeet device, I need to automatically detect which platform a meeting is on.

**Detection Methods:**
1. Calendar event body parsing
   - Meet: `meet.google.com/xxx-xxxx-xxx`
   - Teams: `teams.microsoft.com/l/meetup-join/...`
   - Zoom: `zoom.us/j/xxxxxxxxx`
   - Webex: `*.webex.com/meet/...`

2. URL pattern matching
3. Room preference fallback

**Requirements:**
- [ ] Parse meeting URLs from calendar events
- [ ] Support multiple meeting links in one event
- [ ] Priority ranking when multiple links present
- [ ] Manual platform override option
- [ ] Handle malformed/shortened URLs

### 4.2 Authentication Management (P0)

**User Story:** As an IT admin, I want to configure credentials for each platform.

**Requirements:**
- [ ] Per-platform credential storage
- [ ] OAuth flow support for applicable platforms
- [ ] Session persistence across reboots
- [ ] Automatic re-authentication on session expiry
- [ ] Guest join option when no credentials

**Credential Types:**
| Platform | Auth Type | Credentials |
|----------|-----------|-------------|
| Google Meet | OAuth + Cookie | Google Account |
| Teams | OAuth | Microsoft Account |
| Zoom | OAuth + API | Zoom Account |
| Webex | OAuth | Webex Account |

### 4.3 Meeting Join Flow (P0)

**User Story:** As a room user, I want meetings to join automatically without intervention.

**Join Flow:**
1. Detect upcoming meeting (5 min before)
2. Identify platform from meeting URL
3. Load appropriate provider
4. Navigate to meeting URL
5. Handle authentication if needed
6. Handle lobby/waiting room
7. Join with audio/video enabled
8. Monitor meeting status
9. Leave when meeting ends

**Requirements:**
- [ ] Join meetings within 30 seconds
- [ ] Handle lobby automatically (knock/wait)
- [ ] Retry join on failure (3 attempts)
- [ ] Audio/video enabled by default
- [ ] Handle expired/invalid meeting links

### 4.4 Meeting Controls (P1)

**User Story:** As a room user, I want consistent controls across all platforms.

**Universal Controls:**
| Control | Google Meet | Teams | Zoom | Webex |
|---------|-------------|-------|------|-------|
| Mute/Unmute Audio | ✓ | ✓ | ✓ | ✓ |
| Enable/Disable Video | ✓ | ✓ | ✓ | ✓ |
| Leave Meeting | ✓ | ✓ | ✓ | ✓ |
| Raise Hand | ✓ | ✓ | ✓ | ✓ |
| Screen Share | ✓ | ✓ | ✓ | ✓ |
| View Participants | ✓ | ✓ | ✓ | ✓ |
| Chat (view) | ✓ | ✓ | ✓ | ✓ |

**Requirements:**
- [ ] IR remote integration for controls
- [ ] Keyboard shortcut mapping
- [ ] On-screen controls overlay
- [ ] Consistent control layout

### 4.5 Quality & Monitoring (P2)

**User Story:** As an IT admin, I want visibility into meeting quality.

**Requirements:**
- [ ] Meeting quality metrics per platform
- [ ] Audio/video quality indicators
- [ ] Network bandwidth usage
- [ ] Error logging and reporting
- [ ] Platform-specific diagnostics

---

## 5. Implementation Details

### 5.1 Google Meet (Enhancement)

Current implementation via Minimeet Chrome extension.

**Enhancements:**
- Improve error handling and recovery
- Add meeting quality metrics
- Better lobby handling
- Integration with management dashboard

### 5.2 Microsoft Teams

**Approach:** Browser-based (teams.microsoft.com)

**Implementation Steps:**
1. Create Teams provider module
2. Implement OAuth authentication flow
3. Handle Teams meeting URL parsing
4. Automate meeting join process
5. Implement DOM-based controls
6. Handle Teams-specific UI elements

**Challenges:**
- Teams web client limited compared to desktop
- Authentication complexity
- Frequent UI updates

**Solutions:**
- Use stable DOM selectors
- Implement selector versioning
- Automated testing against Teams web

### 5.3 Zoom

**Approach:** Browser-based (zoom.us/wc)

**Implementation Steps:**
1. Create Zoom provider module
2. Implement Zoom OAuth/JWT authentication
3. Handle meeting ID/password extraction
4. Automate meeting join process
5. Handle waiting room
6. Implement controls

**Challenges:**
- Zoom prefers native client
- Web client prompts for app install
- Some features limited in browser

**Solutions:**
- Block native client redirect
- Use web client directly
- Document feature limitations

### 5.4 Webex

**Approach:** Browser-based (webex.com)

**Implementation Steps:**
1. Create Webex provider module
2. Implement Webex authentication
3. Handle meeting URL variations
4. Automate join process
5. Implement controls

---

## 6. Testing Strategy

### 6.1 Test Matrix

| Scenario | Meet | Teams | Zoom | Webex |
|----------|------|-------|------|-------|
| Join scheduled meeting | ✓ | ✓ | ✓ | ✓ |
| Join with password | N/A | N/A | ✓ | ✓ |
| Handle waiting room | ✓ | ✓ | ✓ | ✓ |
| Guest join | ✓ | ✓ | ✓ | ✓ |
| Leave meeting | ✓ | ✓ | ✓ | ✓ |
| Mute/unmute | ✓ | ✓ | ✓ | ✓ |
| Camera on/off | ✓ | ✓ | ✓ | ✓ |
| Network reconnect | ✓ | ✓ | ✓ | ✓ |

### 6.2 Automated Testing
- Selenium/Playwright tests for each platform
- CI/CD integration
- Nightly regression tests
- Platform update monitoring

---

## 7. Rollout Plan

### Phase 1: Teams Support (2 weeks)
- Implement Teams provider
- Testing and stabilization
- Documentation

### Phase 2: Zoom Support (2 weeks)
- Implement Zoom provider
- Testing and stabilization
- Documentation

### Phase 3: Webex Support (1 week)
- Implement Webex provider
- Testing
- Documentation

### Phase 4: Polish (1 week)
- Cross-platform testing
- Performance optimization
- Documentation finalization

---

## 8. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Platform UI changes | High | High | Version detection, rapid updates |
| Auth flow changes | High | Medium | OAuth, monitor announcements |
| Browser compatibility | Medium | Low | Chrome focus, stable versions |
| Feature parity gaps | Medium | Medium | Document limitations clearly |

---

## 9. Success Criteria

- [ ] All 4 platforms join meetings successfully
- [ ] < 30 second join time for all platforms
- [ ] > 99% join success rate
- [ ] All basic controls working
- [ ] Integration with management dashboard

---

## 10. Appendix

### 10.1 Meeting URL Patterns

```regex
# Google Meet
https?://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}

# Microsoft Teams
https?://teams\.microsoft\.com/l/meetup-join/.*

# Zoom
https?://.*\.?zoom\.us/j/\d+.*

# Webex
https?://.*\.webex\.com/(meet|join)/.*
```

### 10.2 Platform Comparison

| Feature | Meet | Teams | Zoom | Webex |
|---------|------|-------|------|-------|
| Browser support | Excellent | Good | Fair | Good |
| Guest join | Yes | Yes | Yes | Yes |
| HD Video | Yes | Yes | Yes | Yes |
| Screen share | Yes | Yes | Yes | Yes |
| Recording | Host only | Host only | Host only | Host only |
