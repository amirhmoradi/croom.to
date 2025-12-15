<div align="center">

# 🎥 PiMeet Enterprise

### Turn Any Raspberry Pi Into a Professional Video Conferencing System

**The open-source alternative to Cisco Webex Room Kit — for 1/50th the price**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-5%20|%204-red.svg)](https://www.raspberrypi.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub Stars](https://img.shields.io/github/stars/amirhmoradi/pimeet-enhanced?style=social)](https://github.com/amirhmoradi/pimeet-enhanced)
[![Made in France](https://img.shields.io/badge/Made%20in-France-blue.svg)](https://en.wikipedia.org/wiki/French_Tech)
[![Digital Sovereignty](https://img.shields.io/badge/Digital-Sovereignty-purple.svg)](#-digital-sovereignty--data-privacy)

[Features](#-features) • [Quick Start](#-quick-start) • [Sovereignty](#-digital-sovereignty--data-privacy) • [Documentation](#-documentation) • [Contributing](#-contributing)

---

<img src="docs/assets/hero-banner.png" alt="PiMeet Enterprise Dashboard" width="800"/>

*Transform conference rooms with enterprise-grade video conferencing at a fraction of the cost*

</div>

---

## 🇫🇷 Digital Sovereignty & Data Privacy

> **PiMeet is a French initiative** committed to digital resilience, data privacy, and technological independence.

In a world where video conferencing has become critical infrastructure, organizations deserve **control over their communication systems**. PiMeet was created to break free from:

- **Vendor Lock-in**: No dependency on single cloud providers
- **Data Exploitation**: Your meetings, your data — processed locally on your hardware
- **Unpredictable Pricing**: No per-seat licenses that scale against you
- **Opaque Systems**: Fully open source, audit everything

### Our Principles

| Principle | How PiMeet Delivers |
|-----------|---------------------|
| **Data Sovereignty** | All processing happens on YOUR hardware. No cloud required. |
| **Privacy by Design** | AI runs locally via Hailo/Coral. No data leaves your network. |
| **Open Source** | MIT licensed. Inspect, modify, and audit every line of code. |
| **Vendor Independence** | Works with Meet, Teams, Zoom — switch platforms freely. |
| **European Values** | GDPR-ready architecture. Built with privacy regulations in mind. |

### Self-Hosted & Air-Gapped Ready

PiMeet can operate **completely offline** in air-gapped environments:
- No internet required for core functionality
- Local AI processing with Hailo-8L or Coral TPU
- On-premise management dashboard
- Full functionality without external dependencies

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

## 🎙️ Meeting Intelligence with Vexa Integration

PiMeet integrates with [**Vexa**](https://github.com/Vexa-ai/vexa) — the open-source, self-hosted meeting transcription platform — for advanced meeting intelligence features while keeping **all data on your infrastructure**.

### What Vexa Adds to PiMeet

| Feature | Description |
|---------|-------------|
| **Real-time Transcription** | Live transcripts during meetings (100+ languages) |
| **Meeting Summaries** | AI-generated summaries and action items |
| **Searchable Archives** | Find any discussion across all your meetings |
| **Translation** | Real-time translation between 100 languages |
| **Self-Hosted** | Run on your infrastructure — no cloud dependency |

### Why Vexa + PiMeet?

Both projects share the same values:
- **Open Source** (Vexa: Apache 2.0, PiMeet: MIT)
- **Self-Hosted First** — Your data never leaves your network
- **Privacy by Design** — No third-party data processing
- **Enterprise Ready** — Built for organizations that take security seriously

```bash
# Deploy Vexa alongside PiMeet
git clone https://github.com/Vexa-ai/vexa
cd vexa && make all  # CPU mode (add GPU=1 for GPU acceleration)
```

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Infrastructure                          │
│                                                                 │
│  ┌─────────────┐          ┌─────────────┐                      │
│  │   PiMeet    │◄────────►│    Vexa     │                      │
│  │   Device    │ WebSocket│  Instance   │                      │
│  │             │          │             │                      │
│  │ • Camera    │          │ • Whisper   │                      │
│  │ • Audio     │──────────│ • Transcr.  │                      │
│  │ • Display   │  Audio   │ • Summarize │                      │
│  └─────────────┘  Stream  └─────────────┘                      │
│                                                                 │
│  No data leaves your network. Everything runs locally.         │
└─────────────────────────────────────────────────────────────────┘
```

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

## 🏢 Enterprise Offerings (Coming Soon)

While PiMeet is and will always be **100% open source**, we're planning optional enterprise services for organizations that need additional support:

### Open Source (Free Forever)
- Full PiMeet functionality
- Community support via GitHub
- Self-hosted deployment
- All core features included

### Enterprise Support (Planned)
| Service | Description |
|---------|-------------|
| **Priority Support** | SLA-backed response times, dedicated support channel |
| **Professional Services** | Deployment assistance, custom integrations |
| **Training** | Administrator and end-user training programs |
| **Managed Updates** | Tested update packages, security patches |

### Enterprise Features (Planned)
| Feature | Description |
|---------|-------------|
| **SSO Integration** | SAML/OIDC with your identity provider |
| **Advanced Analytics** | Meeting quality scoring, usage reports, ROI dashboards |
| **Compliance Packages** | Pre-configured for GDPR, HIPAA, SOC 2 |
| **Multi-Tenant Management** | MSP/reseller dashboard for managing multiple orgs |
| **Hardware Bundles** | Pre-configured, tested hardware kits |

### Vexa Enterprise Integration (Planned)
| Feature | Description |
|---------|-------------|
| **Managed Vexa Cluster** | Hosted transcription infrastructure |
| **Meeting Intelligence Suite** | Advanced analytics, sentiment analysis, coaching |
| **Compliance Recording** | Automated retention policies, legal hold |
| **API Access** | Programmatic access to transcripts and insights |

> **Interested in enterprise offerings?** [Contact us](mailto:enterprise@pimeet.dev) or [open a discussion](https://github.com/amirhmoradi/pimeet-enhanced/discussions) to share your requirements.

## 📜 License

PiMeet Enterprise is [MIT licensed](LICENSE). Use it freely in personal and commercial projects.

## 🙏 Acknowledgments

- Built on the foundation of the original [PiMeet](https://github.com/pmansour/pimeet) project
- Inspired by enterprise solutions like Cisco Webex Room Kit and Poly Studio
- Meeting intelligence powered by [Vexa](https://github.com/Vexa-ai/vexa) — open-source transcription
- Thanks to all [contributors](https://github.com/amirhmoradi/pimeet-enhanced/graphs/contributors) who make this possible

---

<div align="center">

**⭐ Star us on GitHub — it motivates us a lot!**

[Report Bug](https://github.com/amirhmoradi/pimeet-enhanced/issues) · [Request Feature](https://github.com/amirhmoradi/pimeet-enhanced/issues) · [Join Discussion](https://github.com/amirhmoradi/pimeet-enhanced/discussions)

---

🇫🇷 **A French Initiative for Digital Sovereignty**

*Breaking vendor lock-in. Protecting data privacy. Empowering organizations.*

Made with ❤️ by the PiMeet Community

</div>
