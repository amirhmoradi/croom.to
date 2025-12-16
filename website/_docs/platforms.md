---
title: Meeting Platforms
description: Configure Croom for Google Meet, Microsoft Teams, Zoom, and Webex.
order: 6
---

# Meeting Platform Configuration

Croom supports all major video conferencing platforms out of the box.

## Supported Platforms

| Platform | Join via URL | Join via Code | Calendar Auto-Join |
|----------|-------------|---------------|-------------------|
| Google Meet | ✅ | ✅ | ✅ |
| Microsoft Teams | ✅ | ✅ | ✅ |
| Zoom | ✅ | ✅ | ✅ |
| Cisco Webex | ✅ | ✅ | ✅ |

## Google Meet

### Basic Setup

Google Meet works out of the box. No additional configuration required.

```yaml
platforms:
  google_meet:
    enabled: true
```

### With Google Workspace Account

For better integration, sign in with a Google account:

1. Open Croom settings
2. Go to Platforms → Google Meet
3. Click "Sign in with Google"
4. Sign in with your room's Google account

Benefits of signed-in mode:
- Automatic admission to organization meetings
- Access to Google Chat in meetings
- Better audio/video quality options

### Meeting Entry Methods

```
# URL format
https://meet.google.com/abc-defg-hij

# Meeting code
abc-defg-hij
```

## Microsoft Teams

### Basic Setup (Guest Mode)

Join Teams meetings as a guest:

```yaml
platforms:
  microsoft_teams:
    enabled: true
    mode: "guest"
```

### With Azure AD Account

For full Teams integration:

1. Create an Azure AD application
2. Configure permissions:
   - `Calendars.Read`
   - `OnlineMeetings.Read`
   - `User.Read`

```yaml
platforms:
  microsoft_teams:
    enabled: true
    mode: "authenticated"
    tenant_id: "your-tenant-id"
    client_id: "your-client-id"
```

3. Complete device code authentication on first use

### Teams Rooms Mode

For dedicated room accounts:

```yaml
platforms:
  microsoft_teams:
    enabled: true
    mode: "room"
    resource_email: "room-a@company.com"
```

### Meeting Entry Methods

```
# URL format
https://teams.microsoft.com/l/meetup-join/...

# Meeting ID and passcode
Meeting ID: 123 456 789
Passcode: abc123
```

## Zoom

### Basic Setup

```yaml
platforms:
  zoom:
    enabled: true
```

### With Zoom Rooms License

For Zoom Rooms features:

1. Obtain Zoom Rooms license
2. Configure in Zoom Admin Portal
3. Get activation code

```yaml
platforms:
  zoom:
    enabled: true
    mode: "room"
    activation_code: "your-activation-code"
```

### Meeting Entry Methods

```
# URL format
https://zoom.us/j/12345678901?pwd=...

# Meeting ID
12345678901

# Personal Meeting ID (PMI)
https://zoom.us/my/username
```

### Zoom Settings

```yaml
platforms:
  zoom:
    enabled: true

    # Audio settings
    auto_join_audio: true
    mute_on_entry: false

    # Video settings
    video_on_entry: true
    hd_video: true

    # Meeting settings
    waiting_room_bypass: true  # Requires license

    # Display settings
    speaker_view: true
    show_names: true
```

## Cisco Webex

### Basic Setup

```yaml
platforms:
  webex:
    enabled: true
```

### With Webex Device Registration

For registered Webex devices:

```yaml
platforms:
  webex:
    enabled: true
    mode: "registered"
    registration_code: "your-code"
```

### Meeting Entry Methods

```
# URL format
https://company.webex.com/meet/username

# Meeting number
123 456 789

# Personal Room
company.webex.com/meet/username
```

## Platform Detection

Croom automatically detects the platform from meeting URLs and codes:

```yaml
platforms:
  auto_detect:
    enabled: true
    fallback: "google_meet"  # Default if detection fails
```

Detection patterns:
- `meet.google.com` → Google Meet
- `teams.microsoft.com` → Microsoft Teams
- `zoom.us` or `*.zoom.us` → Zoom
- `*.webex.com` → Cisco Webex

## Meeting URL Configuration

### Custom Domain Support

```yaml
platforms:
  custom_domains:
    google_meet:
      - "meet.company.com"
    zoom:
      - "company.zoom.us"
    webex:
      - "company.webex.com"
```

### URL Rewriting

```yaml
platforms:
  url_rewrite:
    - pattern: "^https://cal\\.company\\.com/(.*)$"
      replacement: "https://meet.google.com/$1"
```

## Browser Settings

All platforms run in Chromium. Configure browser behavior:

```yaml
browser:
  # Cache and storage
  persistent_storage: true
  clear_on_meeting_end: false

  # Performance
  hardware_acceleration: true
  gpu_compositing: true

  # Privacy
  do_not_track: true
  block_third_party_cookies: false

  # Media
  auto_play_policy: "no-user-gesture-required"

  # Display
  default_zoom: 100
  force_dark_mode: false
```

## Troubleshooting

### Meeting won't join

1. Check network connectivity
2. Verify meeting URL/code is correct
3. Check platform is enabled in config
4. View browser console for errors:
   ```bash
   sudo journalctl -u croom -f | grep -i browser
   ```

### Audio/video not working

1. Check camera permissions in browser
2. Verify devices are detected:
   ```bash
   croom devices list
   ```
3. Test with platform's audio/video settings

### Authentication issues

1. Clear browser data:
   ```bash
   croom browser clear
   ```
2. Re-authenticate with platform
3. Check OAuth credentials are valid

### Platform-specific issues

**Google Meet:**
- Ensure third-party cookies allowed for `google.com`

**Microsoft Teams:**
- May require Edge-specific user agent

**Zoom:**
- Web client has some limitations vs desktop
- HD video requires proper Zoom settings

**Webex:**
- Some features require Chrome/Edge

## Next Steps

- [Calendar Integration](/docs/calendar/) - Automatic meeting joins
- [AI Features](/docs/ai-features/) - Enhance meeting experience
- [Touch Screen](/docs/touch-screen/) - Room control interface
