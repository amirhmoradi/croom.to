# PiMeet Enterprise

Transform a Raspberry Pi into an enterprise-grade video conferencing appliance comparable to Cisco Webex Room Kit — at a fraction of the cost.

> **Note**: This is an enhanced enterprise version building on the original [PiMeet project](https://github.com/pmansour/pimeet).

## Features

- **Multi-Platform Support**: Google Meet, Microsoft Teams, Zoom
- **Edge AI Processing**: Auto-framing, noise reduction, occupancy counting (with optional AI accelerator)
- **Touch Screen UI**: Local room management interface
- **Fleet Management**: Centralized dashboard for managing all devices
- **Zero-Touch Provisioning**: Easy deployment at scale
- **Modern Installation**: Non-destructive install on existing Raspberry Pi OS
- **Cross-Platform Architecture**: Pi-first with abstraction for future PC support

## Quick Start

### One-Line Installation

```bash
curl -sSL https://raw.githubusercontent.com/your-org/pimeet-enhanced/main/installer/install.sh | sudo bash
```

### Manual Installation

```bash
git clone https://github.com/your-org/pimeet-enhanced.git
cd pimeet-enhanced
pip install -e .
pimeet -c /etc/pimeet/config.yaml
```

## Cost Comparison

| Feature | Cisco Room Kit | PiMeet Enterprise |
|---------|---------------|-------------------|
| Hardware Cost | $3,000-15,000 | <$250 (with AI) |
| Multi-Platform | Limited | Yes (Meet, Teams, Zoom) |
| Central Management | Control Hub | Dashboard |
| AI Features | Yes | Yes (with accelerator) |
| Monthly Fee | $15/device | Free (open source) |

---

## Background

### Origins
This project builds on the original PiMeet, which uses a Raspberry Pi 4 to turn any room into a cheap conference room that can automatically join meetings on its calendar.

### The Enterprise Challenge
While the original PiMeet solved the cost problem brilliantly, enterprise deployments need additional capabilities:
- Fleet management across many rooms
- Multi-platform support (not just Google Meet)
- AI features for professional meeting quality
- Touch UI for non-technical users
- Remote monitoring and troubleshooting

### Why Raspberry Pi?
Existing enterprise devices cost $3,000-15,000+ per room. For organizations with 10-50 meeting rooms, that's $30,000-750,000 just for hardware. PiMeet Enterprise delivers comparable features for under $250 per room.

## Design goals
This solution was designed to solve the above issues. Specifically, we aim to create a solution that is:

- Easy to deploy to several rooms within an organization.
- Cheap (ideally <$100 per room, excluding the TV and webcam).
- Automated / easy to use.
- Easy to maintain over time.

## PiMeet
### Overview
To solve the above issues, we've built a system that uses a combination of cheap hardware and custom software to turn any room into a meeting room. This system has been tested extensively and has been through several iterations to produce the current fleet, which has been powering the Sunday School classes at St George Coptic Orthodox Church in Kirkland, WA since fall of 2021.

The current name for this device is PiMeet.

### User Experience
One of the goals is to make this dead-simple to use, and hard to get wrong. As such, the UX is incredibly simple:
- When someone enters a room, they turn on the PiMeet device and wait for it to join the next meeting on its calendar.
- When they’re done, they hit the power button again to turn it off.
- *That’s it!*

See these [Quickstart instructions](https://docs.google.com/document/d/11bFKDRnKby4PvWUyqYbBlXx3mhg-zHjduksk8KyJA5A/view), which were printed, laminated and hung in the rooms at St George Coptic Orthodox Church, Kirkland.

<p align="center">
<img src="/docs/room-demo.png" alt="Room configured with PiMeet" />
<br />
<strong>Figure A</strong>: A meeting room configured with PiMeet. Note the raspberry pi mounted directly under the TV and the quickstart instructions laminated next to it.
</p>

Each PiMeet device has its own Google account[^1] with its own calendar, and the device will just join the next meeting on its calendar. Anybody within the organization can schedule a Google Meet[^2] meeting and invite the room’s account to it, and when they turn on the PiMeet it will just automagically join that new meeting.

[^1]: For example, `mezzanine-room@{your-domain}.org`
[^2]: The system already has experimental Zoom support (through Zoom Web), but the performance of Zoom Web is not very responsive when content is being presented. This will hopefully get better over time.

PiMeet achieves those goals by configuring a Raspberry PI 4B to be a 1-click meeting room device. In a nutshell, each device runs [Raspberry PI OS](https://www.raspberrypi.com/software/) (a Debian Linux fork), specially configured to run Chromium on startup with the [Minimeet extension](https://github.com/pmansour/minimeet). This extension logs into its configured Google account and joins the next available meeting on its calendar.

<p align="center">
<img src="/docs/create-meeting.png" alt="Creating a meeting using Google Calendar" />
<br />
<strong>Figure B</strong>: Inviting a room's account (<code>grade3-room@{your-domain}.org</code>) to a new meeting. This works for ad-hoc as well as recurring (e.g. weekly or daily) meetings.
</p>

### Hardware components
As of today, a typical deployment consists of the following hardware:
- **Raspberry Pi 4B 4GB**. This model costs $55 MSRP[^3] (see [official resellers](https://www.raspberrypi.com/products/raspberry-pi-4-model-b#find-reseller)), and has powerful-enough specs[^4] to produce smooth, lag-free meetings consistently.
- **Raspberry Pi accessories**. This includes a 32GB microSD card (~$6 on [Amazon](https://www.amazon.com/dp/B07NP96DX5)), a HDMI-to-HDMI cable ($5 on [Amazon](https://www.amazon.com/dp/B01H7M6YKI)), and a USB-C power supply ($10 on [Amazon](https://www.amazon.com/dp/B07TYQRXTK)).
- **ArgonOne V.2 case**. This case costs $25 on [Amazon](https://www.amazon.com/dp/B07WP8WC3V), and has excellent cooling, ports, form-factor as well as a physical safe-shutdown power button and an IR sensor that allows use of a remote control.
- **Logitech C920x Webcam**. This webcam costs $60 on [Amazon](https://www.amazon.com/dp/B085TFF7M1), and produces smooth 1080p video while also including a dual-microphone. In most small rooms, this mic is good enough that no external audio solution is needed.

Aside from the camera, the essentials total about $100 USD at current prices. You can often get discounts when buying in bulk (especially for cables and microSD cards).

In addition to these basics, some optional additions may make for a better UX in some rooms:
- **JabraSpeak 510 bluetooth speaker**. This wireless speaker/microphone combo costs $115 on [Amazon](https://www.amazon.com/dp/B00C3XW5L4). It produces great echo-free audio and has reliable wireless connectivity through the provided dongle. For larger rooms, consider buying multiple [Jabra 710](https://www.amazon.com/dp/B071CGH8YF)s since they can daisy-chain together.
- **Sparkfun IR remote**. This little remote-control costs $4.50 at [Sparkfun](https://www.sparkfun.com/products/14865). It allows for operating the PiMeet device wirelessly without having to press the physical power button.
- **Cheap bluetooth mouse**. You can buy a pack of 10 for $45 (~$4.50 each) on [Amazon](https://www.amazon.com/gp/product/B087CR8RD1). Having a dedicated mouse in each room not only allows for troubleshooting as necessary, but enables some advanced room controls such as explicitly admitting people into each meeting.

[^3]: Due to the current supply-chain crisis, it may be hard to procure these at MSRP in large quantities right now. However, stock is constantly being replenished, so hopefully soon this will not be an issue in a few months.
[^4]: Quad-core CPU, 4GB RAM, USB-3 controller and ports, 2x [micro-]HDMI ports with HDMI-CEC.

### Software components
The PiMeet system consists of a 64-bit Raspberry Pi OS image, with several customizations and configurations to enable smooth video conferencing, various credentials (WiFi networks, fleet admin account, room-specific meeting account), some systemd services and autostart applications to enable complete automation, as well as a copy of the [Minimeet Chrome extension](https://github.com/pmansour/minimeet). The latter is an extension that automates the process of logging in to Google Meet and joining a meeting hands-free.

The process of imaging a new microSD card and configuring its credentials is automated through the three [build scripts](build/) in the PiMeet GitHub repository. Imaging a new device only takes a few minutes and requires no specialized knowledge other than the ability to execute bash scripts.

## Set up
Installing this system in a room involves a few steps:
1. Mount a TV in a good location.
1. Assemble a new raspberry pi in the ArgonOne V2 case, write a new image onto a microSD card and insert it. Now you have a PiMeet device.
1. Attach the PiMeet device to the bottom of the TV using these command stickers. See the pictures in the Quickstart guide above for inspiration.
1. Attach the webcam either on top of the TV, or at the bottom (using more command stickers).
1. Connect the webcam, HDMI and power cables to the PiMeet device, and use cable fasteners and sleeves to hide the complexity.
1. Turn on the power.

## Feedback
If you have questions, feedback or suggestions, you're welcome to file issues on GitHub or send an email to `pimeet-help@googlegroups.com`.
