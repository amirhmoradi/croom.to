<div align="center">

# 🎥 PiMeet Enterprise

### Turn Any Raspberry Pi Into a Professional Video Conferencing System

**The open-source alternative to Cisco Webex Room Kit — for 1/50th the price**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-5%20|%204-red.svg)](https://www.raspberrypi.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub Stars](https://img.shields.io/github/stars/amirhmoradi/pimeet-enhanced?style=social)](https://github.com/amirhmoradi/pimeet-enhanced)

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing) • [Community](#-community)

---

<img src="docs/assets/hero-banner.png" alt="PiMeet Enterprise Dashboard" width="800"/>

*Transform conference rooms with enterprise-grade video conferencing at a fraction of the cost*

</div>

## 💰 Why PiMeet?

| | Cisco Room Kit | Poly Studio | **PiMeet Enterprise** |
|---|:---:|:---:|:---:|
| **Hardware Cost** | $3,000 - $15,000 | $2,000 - $8,000 | **< $250** |
| **Monthly License** | $15/device | $12/device | **Free forever** |
| **10 Rooms (Year 1)** | $31,800+ | $21,440+ | **$2,500** |
| **Multi-platform** | Limited | Limited | **✅ Meet, Teams, Zoom** |
| **AI Features** | ✅ | ✅ | **✅** |
| **Open Source** | ❌ | ❌ | **✅** |

> **Save $29,000+ per year** on a 10-room deployment while getting the same enterprise features.

## ✨ Features

<table>
<tr>
<td width="50%">

### 🖥️ Multi-Platform Support
- **Google Meet** - Full support with calendar integration
- **Microsoft Teams** - Join any Teams meeting
- **Zoom** - Works with Zoom web client
- Auto-detect platform from meeting URL

</td>
<td width="50%">

### 🤖 Edge AI Processing
- **Auto-framing** - Keeps participants in frame
- **Noise reduction** - Crystal clear audio
- **Occupancy counting** - Room analytics
- Works with Hailo-8L, Coral, or CPU fallback

</td>
</tr>
<tr>
<td width="50%">

### 📱 Touch Screen UI
- Beautiful room control interface
- One-tap meeting join
- Calendar view for scheduled meetings
- Camera/mic controls

</td>
<td width="50%">

### 🏢 Fleet Management
- Centralized dashboard for all devices
- Real-time device status monitoring
- Remote configuration & updates
- Usage analytics & reporting

</td>
</tr>
<tr>
<td width="50%">

### 🔧 Zero-Touch Provisioning
- QR code based device enrollment
- Automatic configuration sync
- No manual setup per device
- Scale to hundreds of rooms

</td>
<td width="50%">

### 🔒 Enterprise Security
- End-to-end encryption
- Role-based access control
- Audit logging
- On-premise deployment option

</td>
</tr>
</table>

## 🚀 Quick Start

### One-Line Installation

```bash
curl -sSL https://pimeet.dev/install.sh | sudo bash
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/amirhmoradi/pimeet-enhanced.git
cd pimeet-enhanced

# Install PiMeet
pip install -e .

# Start the agent
pimeet --config /etc/pimeet/config.yaml
```

### Docker (Dashboard)

```bash
docker-compose up -d
```

Open `http://localhost:3000` to access the management dashboard.

## 🛠️ Hardware Requirements

### Recommended Setup (~$200)

| Component | Model | Price |
|-----------|-------|-------|
| Computer | Raspberry Pi 5 (4GB) | $60 |
| Case | Argon ONE V3 | $25 |
| Camera | Logitech C920 | $60 |
| AI Accelerator | Hailo-8L AI Kit | $70 |
| Storage | 32GB microSD | $10 |
| **Total** | | **~$225** |

### Minimum Setup (~$100)

| Component | Model | Price |
|-----------|-------|-------|
| Computer | Raspberry Pi 4 (4GB) | $55 |
| Camera | Generic USB Webcam | $20 |
| Storage | 32GB microSD | $10 |
| Power + Cables | | $15 |
| **Total** | | **~$100** |

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PiMeet Device                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Touch UI   │  │   Agent     │  │  AI Engine  │             │
│  │   (Qt6)     │  │  (Python)   │  │  (Hailo/    │             │
│  │             │  │             │  │   Coral)    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└────────────────────────────┬────────────────────────────────────┘
                             │ WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Management Dashboard                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   React     │  │   Node.js   │  │ PostgreSQL  │             │
│  │  Frontend   │◄─┤   Backend   │◄─┤  Database   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## 📖 Documentation

| Guide | Description |
|-------|-------------|
| [📘 User Guide](docs/guides/user-guide.md) | End-user instructions |
| [📗 Admin Guide](docs/guides/administrator-guide.md) | IT administrator setup |
| [📙 Deployment Guide](docs/guides/deployment-guide.md) | Large-scale rollout |
| [📕 API Reference](docs/api/README.md) | REST & WebSocket APIs |
| [🗺️ Roadmap](docs/roadmap/enterprise-roadmap.md) | Future development plans |

### Product Requirements
- [PRD-001: Management Dashboard](docs/prd/001-management-dashboard.md)
- [PRD-005: Touch Screen UI](docs/prd/005-touch-screen-room-ui.md)
- [PRD-006: Edge AI Features](docs/prd/006-edge-ai-features.md)
- [PRD-008: Cross-Platform Architecture](docs/prd/008-cross-platform-architecture.md)

## 🤝 Contributing

We love contributions! PiMeet is built by the community, for the community.

### Ways to Contribute

- 🐛 **Report Bugs** - Found an issue? [Open a bug report](https://github.com/amirhmoradi/pimeet-enhanced/issues/new?template=bug_report.md)
- 💡 **Request Features** - Have an idea? [Submit a feature request](https://github.com/amirhmoradi/pimeet-enhanced/issues/new?template=feature_request.md)
- 📝 **Improve Docs** - Help us make documentation better
- 💻 **Submit PRs** - Code contributions are welcome!
- ⭐ **Star the Repo** - Show your support!

See our [Contributing Guide](CONTRIBUTING.md) for detailed instructions.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/amirhmoradi/pimeet-enhanced.git
cd pimeet-enhanced

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start development servers
make dev
```

## 🌟 Community

- 💬 [GitHub Discussions](https://github.com/amirhmoradi/pimeet-enhanced/discussions) - Ask questions, share ideas
- 🐛 [Issue Tracker](https://github.com/amirhmoradi/pimeet-enhanced/issues) - Report bugs, request features
- 📧 [Mailing List](mailto:pimeet-help@googlegroups.com) - Stay updated

### Contributors

<a href="https://github.com/amirhmoradi/pimeet-enhanced/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=amirhmoradi/pimeet-enhanced" />
</a>

## 📜 License

PiMeet Enterprise is [MIT licensed](LICENSE). Use it freely in personal and commercial projects.

## 🙏 Acknowledgments

- Built on the foundation of the original [PiMeet](https://github.com/pmansour/pimeet) project
- Inspired by enterprise solutions like Cisco Webex Room Kit and Poly Studio
- Thanks to all [contributors](https://github.com/amirhmoradi/pimeet-enhanced/graphs/contributors) who make this possible

---

<div align="center">

**⭐ Star us on GitHub — it motivates us a lot!**

[Report Bug](https://github.com/amirhmoradi/pimeet-enhanced/issues) · [Request Feature](https://github.com/amirhmoradi/pimeet-enhanced/issues) · [Join Discussion](https://github.com/amirhmoradi/pimeet-enhanced/discussions)

Made with ❤️ by the PiMeet Community

</div>
