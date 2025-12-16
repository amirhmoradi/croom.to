# Croom Deployment Guide

## Introduction

This guide provides step-by-step instructions for deploying Croom in your organization, from initial planning through to production deployment.

---

## Table of Contents

1. [Planning](#1-planning)
2. [Prerequisites](#2-prerequisites)
3. [Dashboard Deployment](#3-dashboard-deployment)
4. [Device Preparation](#4-device-preparation)
5. [Room Setup](#5-room-setup)
6. [Testing](#6-testing)
7. [Rollout](#7-rollout)
8. [Post-Deployment](#8-post-deployment)

---

## 1. Planning

### 1.1 Site Assessment

For each conference room, document:

| Item | Details | Example |
|------|---------|---------|
| Room name | Official room identifier | "Conference Room A" |
| Location | Building, floor, room number | "Building 1, Floor 2, Room 201" |
| Capacity | Number of seats | 8 people |
| TV location | Where TV is mounted/placed | Wall-mounted, north wall |
| Power outlets | Available power sources | 2 outlets near TV |
| Network | WiFi or Ethernet available | WiFi (CorpWiFi) |
| Existing equipment | Current AV equipment | Projector, whiteboard |

### 1.2 Network Planning

```
Network Requirements Checklist:
[ ] WiFi coverage in all rooms
[ ] SSID and credentials for Croom devices
[ ] Firewall rules approved (see below)
[ ] DHCP reservations or static IPs (optional)
[ ] Network monitoring configured
```

**Required Firewall Rules (Outbound):**
```
Protocol  Port      Destination              Purpose
TCP       443       *.google.com             Google Meet
TCP       443       *.microsoft.com          Microsoft Teams
TCP       443       *.zoom.us                Zoom
TCP       443       dashboard.company.com    Management
UDP       3478      *                        STUN/TURN
UDP       10000-20000  *                     Media (WebRTC)
```

### 1.3 Account Planning

**Meeting Accounts:**
Create dedicated accounts for each room:
- `room-a@company.com` → Conference Room A
- `room-b@company.com` → Conference Room B

**Account Requirements:**
| Platform | Account Type | Requirements |
|----------|-------------|--------------|
| Google Meet | Google Workspace | Calendar access, Meet access |
| Microsoft Teams | Microsoft 365 | Teams license, Calendar |
| Zoom | Zoom account | Basic or higher license |

### 1.4 Hardware Planning

**Per Room (Standard Setup):**
| Item | Quantity | Est. Cost |
|------|----------|-----------|
| Raspberry Pi 4B 4GB | 1 | $55 |
| 32GB microSD (Class 10) | 1 | $10 |
| USB-C Power Supply (Official) | 1 | $8 |
| ArgonOne V2 Case | 1 | $25 |
| Logitech C920 Webcam | 1 | $70 |
| HDMI Cable (2m) | 1 | $10 |
| **Total per room** | | **~$178** |

**Optional Enhancements:**
| Item | Purpose | Est. Cost |
|------|---------|-----------|
| Jabra Speak 510 | Better audio | $100 |
| PTZ Camera | Larger rooms | $200-500 |
| IR Receiver | Remote control | $10 |

### 1.5 Timeline Example

| Phase | Duration | Activities |
|-------|----------|------------|
| Planning | 1 week | Site assessment, network planning |
| Procurement | 2 weeks | Order hardware, create accounts |
| Dashboard Setup | 1 day | Deploy management dashboard |
| Pilot | 1 week | Deploy 2-3 rooms, test, refine |
| Rollout | 2 weeks | Deploy remaining rooms |
| Training | 1 week | User training, documentation |

---

## 2. Prerequisites

### 2.1 Hardware Received

```
Checklist per device:
[ ] Raspberry Pi 4B (4GB recommended)
[ ] MicroSD card (32GB Class 10)
[ ] USB-C power supply (5V 3A)
[ ] Case with cooling (ArgonOne recommended)
[ ] Webcam (Logitech C920/C922)
[ ] HDMI cable
```

### 2.2 Accounts Created

```
For each room:
[ ] Meeting account created (room-X@company.com)
[ ] Calendar shared with appropriate users
[ ] Meeting platform license assigned
[ ] Password documented securely
```

### 2.3 Network Ready

```
[ ] WiFi credentials documented
[ ] Firewall rules implemented
[ ] Test device can reach required endpoints
[ ] Dashboard server network access confirmed
```

### 2.4 Build Machine Ready

For image preparation, you need:
- Ubuntu 20.04+ workstation/VM
- SD card reader
- Required tools installed:

```bash
# Install prerequisites
sudo apt update
sudo apt install -y git wget xz-utils tree
```

---

## 3. Dashboard Deployment

### 3.1 Server Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Storage | 50 GB | 100 GB |
| OS | Ubuntu 20.04+, Docker | Ubuntu 22.04 LTS |

### 3.2 Docker Deployment (Recommended)

```bash
# Clone repository
git clone https://github.com/amirhmoradi/croom.to-dashboard.git
cd croom-dashboard

# Configure environment
cp .env.example .env
nano .env
```

**Edit `.env`:**
```bash
# Database
POSTGRES_PASSWORD=your-secure-password
DATABASE_URL=postgresql://croom:your-secure-password@db:5432/croom

# Security
SECRET_KEY=your-very-long-random-secret-key
ALLOWED_HOSTS=croom.yourcompany.com

# Email (for alerts)
EMAIL_HOST=smtp.yourcompany.com
EMAIL_PORT=587
EMAIL_USER=croom@yourcompany.com
EMAIL_PASSWORD=email-password

# Admin
ADMIN_EMAIL=admin@yourcompany.com
```

**Start services:**
```bash
# Start containers
docker-compose up -d

# Create admin user
docker exec -it croom-dashboard ./manage.py createsuperuser

# Verify running
docker-compose ps
curl https://localhost/health
```

### 3.3 SSL Certificate

**Using Let's Encrypt:**
```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d croom.yourcompany.com

# Update nginx config
# Certificates are at /etc/letsencrypt/live/croom.yourcompany.com/
```

**Using Internal CA:**
```bash
# Place certificates in
/etc/croom/certs/server.crt
/etc/croom/certs/server.key

# Update docker-compose.yml to mount certificates
```

### 3.4 Initial Configuration

1. **Login to Dashboard**
   ```
   URL: https://croom.yourcompany.com
   User: admin@yourcompany.com
   Password: [created during setup]
   ```

2. **Configure Organization**
   - Settings → Organization → Update name and details
   - Settings → Locations → Add your buildings/floors

3. **Create Device Groups**
   - Devices → Groups → Create groups by location

4. **Configure Alerts**
   - Settings → Alerts → Enable email/Slack notifications

5. **Generate Enrollment Token**
   - Settings → Enrollment → Generate Token
   - Copy token for device provisioning

---

## 4. Device Preparation

### 4.1 Download or Build Image

**Option A: Download Pre-built Image**
```bash
# Download latest release
wget https://github.com/amirhmoradi/croom.to/releases/latest/download/croom-latest.img.gz
gunzip croom-latest.img.gz
```

**Option B: Build Custom Image**
```bash
# Clone repository
git clone https://github.com/amirhmoradi/croom.to.git
cd croom/build

# Download base OS
./download-img.sh

# Prepare image (interactive)
./prep-img.sh
```

During `prep-img.sh`, you'll be prompted for:
- Device password (for SSH access)
- WiFi networks (SSID and password)
- Dashboard URL
- Enrollment token

### 4.2 Flash SD Cards

**Single Card:**
```bash
# Insert SD card and identify device
lsblk

# Flash image (CAREFUL: this erases the device!)
sudo dd if=croom-latest.img of=/dev/sdX bs=4M status=progress
sync
```

**Multiple Cards (Batch):**
```bash
# Using Balena Etcher (GUI)
# Or parallel dd:
for dev in /dev/sd{b,c,d,e}; do
    sudo dd if=croom-latest.img of=$dev bs=4M status=progress &
done
wait
sync
```

### 4.3 Label Devices

Create labels for each device:
```
┌────────────────────────┐
│ Croom Device          │
│ Room: Conference A     │
│ MAC: aa:bb:cc:dd:ee:ff │
│ Serial: PI-2025-001    │
└────────────────────────┘
```

Attach label to device and keep record in inventory.

---

## 5. Room Setup

### 5.1 Hardware Installation

**Step 1: Assemble Device**
```
1. Install Pi in case (ArgonOne)
2. Insert prepared SD card
3. Connect webcam via USB
4. DO NOT power on yet
```

**Step 2: Position Equipment**
```
1. Mount/place webcam (ideally eye-level, centered on TV)
2. Route cables neatly
3. Ensure clear camera view of meeting area
4. Position for good audio pickup
```

**Step 3: Connect to TV**
```
1. Connect HDMI cable to TV
2. Connect power supply to Pi
3. Turn on TV and select correct HDMI input
```

### 5.2 Initial Boot and Setup

**If using Captive Portal:**
```
1. Device boots and creates WiFi network "Croom-Setup-XXXX"
2. TV displays setup instructions and QR code
3. Connect phone/laptop to Croom-Setup network
4. Browser auto-opens or navigate to 192.168.4.1
5. Complete setup wizard:
   - Select WiFi network
   - Enter WiFi password
   - Enter meeting credentials
   - Name the room
6. Device reboots and connects to network
7. Device appears in dashboard
```

**If using Pre-configured Image:**
```
1. Device boots and auto-connects to WiFi
2. Device registers with dashboard
3. Device appears in dashboard as "Pending Setup"
4. Complete configuration in dashboard:
   - Assign to room
   - Configure credentials
   - Apply configuration template
```

### 5.3 Dashboard Configuration

1. **Find Device in Dashboard**
   - Devices → New Devices (or search by MAC)

2. **Assign to Room**
   - Click device → Edit → Set name and location

3. **Configure Credentials**
   - Configuration → Meeting Credentials
   - Select platform and enter credentials
   - Test connection

4. **Apply Template (Optional)**
   - Configuration → Apply Template
   - Select "Standard Conference Room"

5. **Verify Status**
   - Device shows "Online" status
   - Calendar syncing shows events
   - Test meeting join

### 5.4 Verification Checklist

```
Per Room Verification:
[ ] Device powered on and online in dashboard
[ ] WiFi connected with good signal
[ ] Video: Webcam shows in meeting
[ ] Audio: Can hear and be heard in meeting
[ ] Calendar: Shows upcoming meetings
[ ] Join: Successfully joins test meeting
[ ] Leave: Meeting ends cleanly
[ ] TV Control: TV turns on/off with device (if HDMI-CEC)
```

---

## 6. Testing

### 6.1 Individual Room Test

**Test Script:**
```
1. Create test meeting 5 minutes in future
   - Invite room calendar
   - Use each platform (Meet, Teams, Zoom)

2. Verify auto-join
   - Device should join within 1 minute of meeting start
   - Video should be enabled
   - Audio should be enabled

3. Test basic controls
   - Mute/unmute audio
   - Enable/disable camera
   - Leave meeting

4. Test end-of-meeting
   - End meeting from another device
   - Room should return to idle state

5. Document results
```

### 6.2 Multi-Room Test

**Concurrent Meeting Test:**
```
1. Schedule meetings in all rooms at same time
2. Verify all devices join successfully
3. Check dashboard shows all devices in meeting
4. End meetings and verify all return to idle
```

### 6.3 Edge Case Testing

| Scenario | Test | Expected Result |
|----------|------|-----------------|
| Network loss | Disconnect WiFi briefly | Reconnects automatically |
| Power loss | Unplug and replug | Reboots and rejoins |
| Double-book | Two meetings at same time | Joins first meeting |
| No meeting | No calendar events | Shows idle screen |
| Long meeting | 2+ hour meeting | Stays connected |

### 6.4 User Acceptance Test

```
1. Select pilot users from each department
2. Have them use rooms for real meetings
3. Collect feedback:
   - Ease of use
   - Audio/video quality
   - Any issues encountered
4. Address feedback before full rollout
```

---

## 7. Rollout

### 7.1 Rollout Strategy

**Option A: Phased Rollout (Recommended)**
```
Week 1: Building 1 (5 rooms)
Week 2: Building 2 (5 rooms)
Week 3: Building 3 (5 rooms)
Week 4: Remaining rooms
```

**Option B: Big Bang**
```
All rooms in single weekend
- Higher risk
- Faster completion
- Requires more resources
```

### 7.2 Communication Plan

**Announcement (1 week before):**
```
Subject: New Video Conferencing System Coming to Meeting Rooms

Dear team,

We're excited to announce that [Conference Room Names] will be
upgraded with Croom, a new video conferencing system.

What's changing:
- Rooms will automatically join scheduled meetings
- No more laptop dongles needed
- Works with Google Meet, Teams, and Zoom

What you need to do:
- Invite the room to your meetings (room-name@company.com)
- The system handles the rest!

Training sessions:
- [Date/Time] - Introduction to Croom
- [Date/Time] - Q&A Session

Quick reference guides will be posted in each room.

Questions? Contact IT at [email/phone]
```

### 7.3 Training Materials

**User Training (15 minutes):**
1. How Croom works (2 min)
2. Scheduling meetings with room (3 min)
3. What to expect when entering room (3 min)
4. Basic controls (5 min)
5. Troubleshooting basics (2 min)

**IT Staff Training (1 hour):**
1. System architecture (10 min)
2. Dashboard walkthrough (15 min)
3. Common troubleshooting (15 min)
4. Escalation procedures (10 min)
5. Hands-on practice (10 min)

### 7.4 Go-Live Checklist

```
Pre-Go-Live:
[ ] All rooms tested and verified
[ ] Dashboard fully configured
[ ] Alerts configured and tested
[ ] Documentation complete
[ ] Help desk trained
[ ] User communication sent
[ ] Quick reference cards printed and posted

Go-Live Day:
[ ] IT support available (in-person or on-call)
[ ] Monitor dashboard for issues
[ ] Respond to user feedback quickly
[ ] Document any issues for post-mortem

Post-Go-Live:
[ ] Review meeting success rates
[ ] Address any reported issues
[ ] Collect user feedback
[ ] Plan improvements
```

---

## 8. Post-Deployment

### 8.1 Monitoring Setup

**Dashboard Checks (Daily):**
- All devices online
- No critical alerts
- Meeting success rate >99%

**Weekly Report:**
- Device uptime statistics
- Meeting counts by room
- Any recurring issues

### 8.2 Support Procedures

**Tier 1 (Help Desk):**
```
Common requests and solutions:
- "Meeting didn't start" → Check calendar invite
- "No audio" → Check volume, verify unmuted
- "No video" → Verify camera connected
- "Device offline" → Check TV power, network
```

**Tier 2 (IT Admin):**
```
Escalation triggers:
- Device offline >30 minutes
- Repeated meeting failures
- Hardware issues
- Configuration problems
```

**Escalation Path:**
```
User → Help Desk → IT Admin → Vendor (if hardware)
```

### 8.3 Maintenance Schedule

**Weekly:**
- Review alerts and resolve
- Check for available updates

**Monthly:**
- Apply software updates
- Review performance metrics
- Check hardware health

**Quarterly:**
- Security review
- Credential rotation
- Capacity planning

### 8.4 Success Metrics

Track these metrics to measure success:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Device Uptime | >99.5% | Dashboard metrics |
| Meeting Join Success | >99% | Dashboard metrics |
| User Satisfaction | >4/5 | Survey |
| Support Tickets | <1 per room/month | Help desk data |
| Setup Time | <10 min per room | Deployment log |

---

## Appendix

### A. Inventory Template

```csv
Device ID,MAC Address,Room Name,Location,Install Date,Status
PI-001,aa:bb:cc:dd:ee:01,Conference A,Bldg 1 Fl 2,2025-01-15,Active
PI-002,aa:bb:cc:dd:ee:02,Conference B,Bldg 1 Fl 2,2025-01-15,Active
PI-003,aa:bb:cc:dd:ee:03,Board Room,Bldg 1 Fl 3,2025-01-16,Active
```

### B. Quick Reference Card Template

```
╔════════════════════════════════════════════════╗
║              Croom Quick Guide                ║
╠════════════════════════════════════════════════╣
║                                                ║
║  STARTING A MEETING                            ║
║  1. Turn on TV                                 ║
║  2. Meeting joins automatically!               ║
║                                                ║
║  CONTROLS                                      ║
║  🎤 Tap microphone icon to mute                ║
║  📷 Tap camera icon to turn off video          ║
║  📞 Tap red button to leave meeting            ║
║                                                ║
║  SCHEDULE MEETINGS                             ║
║  Invite: room-name@company.com                 ║
║                                                ║
║  PROBLEMS?                                     ║
║  Call IT: x1234 or it-help@company.com         ║
║                                                ║
╚════════════════════════════════════════════════╝
```

### C. Troubleshooting Decision Tree

```
Meeting not joining?
├── Is TV on?
│   └── No → Turn on TV
│   └── Yes → Continue
├── Is correct HDMI input selected?
│   └── No → Select correct input
│   └── Yes → Continue
├── Does screen show Croom?
│   └── No → Check device power
│   └── Yes → Continue
├── Does screen show "Offline"?
│   └── Yes → Check network/call IT
│   └── No → Continue
├── Is meeting on calendar?
│   └── No → Invite room to meeting
│   └── Yes → Continue
└── Still not working?
    └── Contact IT support
```

---

## Version Information

| Document | Version |
|----------|---------|
| Deployment Guide | 1.0 |
| Last Updated | 2025-12-15 |
