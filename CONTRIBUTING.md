# Contributing to Croom

First off, thank you for considering contributing to Croom! 🎉

It's people like you that make Croom such a great tool for transforming conference rooms around the world. We welcome contributions from everyone, whether it's:

- 🐛 Reporting a bug
- 💡 Suggesting a feature
- 📝 Improving documentation
- 💻 Writing code
- 🧪 Testing and providing feedback
- 🌍 Translating to other languages

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:

- **Be respectful** - Treat everyone with respect. No harassment, discrimination, or offensive behavior.
- **Be constructive** - Provide helpful feedback. Avoid personal attacks.
- **Be collaborative** - Work together toward common goals. Share knowledge freely.
- **Be patient** - Remember that everyone was new once. Help newcomers learn.

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Python 3.10+** installed
- **Node.js 18+** (for dashboard development)
- **Git** for version control
- A **GitHub account**

For device testing:
- Raspberry Pi 4 or 5 (recommended)
- USB webcam
- Microphone/speaker

### Fork and Clone

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:

```bash
git clone https://github.com/YOUR-USERNAME/croom.git
cd croom
```

3. **Add upstream** remote:

```bash
git remote add upstream https://github.com/amirhmoradi/croom.git
```

4. **Keep your fork synced**:

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

## Development Environment

### Python Setup (Core Agent)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
croom --version
```

### Dashboard Backend (Node.js)

```bash
cd src/croom-dashboard/backend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Dashboard Frontend (React)

```bash
cd src/croom-dashboard/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Touch UI (Qt/QML)

```bash
# Install Qt dependencies (Debian/Ubuntu)
sudo apt install python3-pyside6.qtcore python3-pyside6.qtgui \
    python3-pyside6.qtwidgets python3-pyside6.qtqml python3-pyside6.qtquick

# Run Touch UI
python -m croom_ui.main --windowed --debug
```

### All-in-One Development

```bash
# Start everything (requires tmux or multiple terminals)
make dev

# Or individually:
make dev-agent      # Start Croom agent
make dev-dashboard  # Start dashboard backend + frontend
make dev-ui         # Start Touch UI
```

## How to Contribute

### 🐛 Reporting Bugs

Found a bug? Please help us fix it!

1. **Search existing issues** to avoid duplicates
2. **Open a new issue** using the bug report template
3. **Include details**:
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots/logs if applicable
   - Environment info (OS, Python version, hardware)

```markdown
### Bug Description
[Clear description of the bug]

### Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Environment
- OS: Raspberry Pi OS Bookworm
- Python: 3.11
- Hardware: Pi 5, Hailo-8L
```

### 💡 Suggesting Features

Have an idea? We'd love to hear it!

1. **Check the roadmap** first: [docs/roadmap/enterprise-roadmap.md](docs/roadmap/enterprise-roadmap.md)
2. **Search existing issues** for similar suggestions
3. **Open a feature request** with:
   - Problem you're trying to solve
   - Proposed solution
   - Alternative approaches considered
   - Potential impact on existing features

### 💻 Contributing Code

Ready to write some code? Here's how:

1. **Find an issue** to work on
   - Look for `good first issue` labels for beginners
   - Look for `help wanted` labels for more challenging tasks
   - Comment on the issue to claim it

2. **Create a branch**:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

3. **Make your changes** following our [coding standards](#coding-standards)

4. **Write tests** for new functionality

5. **Run tests locally**:

```bash
pytest
```

6. **Commit your changes**:

```bash
git add .
git commit -m "feat: add awesome new feature"
```

Use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting)
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

7. **Push and create PR**:

```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub.

## Pull Request Process

### Before Submitting

- [ ] Code follows our style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests pass locally
- [ ] Branch is up to date with main

### PR Template

```markdown
## Description
[Brief description of changes]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (specify)

## Related Issues
Closes #123

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Tested on real hardware

## Screenshots (if applicable)
[Add screenshots]

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Tests added
```

### Review Process

1. **Automated checks** run on your PR
2. **Maintainers review** your code
3. **Address feedback** if requested
4. **PR gets merged** once approved! 🎉

## Coding Standards

### Python (PEP 8 + extras)

```python
# Use type hints
def process_frame(frame: np.ndarray, threshold: float = 0.5) -> List[Detection]:
    """Process a video frame for detections.

    Args:
        frame: Input frame as numpy array (HWC, BGR)
        threshold: Minimum confidence threshold

    Returns:
        List of detected objects
    """
    pass

# Use dataclasses for data structures
@dataclass
class Detection:
    class_id: int
    confidence: float
    bbox: Tuple[float, float, float, float]

# Async functions for I/O operations
async def fetch_calendar_events(calendar_id: str) -> List[Event]:
    pass
```

### TypeScript (Dashboard)

```typescript
// Use interfaces for types
interface Device {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'error';
  lastSeen: Date;
}

// Use async/await
async function fetchDevices(): Promise<Device[]> {
  const response = await api.get('/devices');
  return response.data.devices;
}

// React components with TypeScript
interface DeviceCardProps {
  device: Device;
  onSelect?: (device: Device) => void;
}

export function DeviceCard({ device, onSelect }: DeviceCardProps) {
  return (
    <div onClick={() => onSelect?.(device)}>
      {device.name}
    </div>
  );
}
```

### Formatting

```bash
# Python - use black and ruff
black src/
ruff check src/ --fix

# TypeScript - use prettier and eslint
npm run lint
npm run format
```

## Testing Guidelines

### Python Tests

```python
# tests/unit/test_detector.py
import pytest
from croom.platform.detector import PlatformDetector

def test_detect_raspberry_pi(mock_pi_environment):
    """Test detection on Raspberry Pi hardware."""
    info = PlatformDetector.detect()
    assert info.device.value.startswith('rpi')

@pytest.mark.asyncio
async def test_ai_inference():
    """Test AI inference returns valid results."""
    backend = MockAIBackend()
    result = await backend.infer(mock_frame)
    assert len(result.detections) >= 0
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=croom

# Specific module
pytest tests/unit/test_meeting.py

# Verbose output
pytest -v
```

### Integration Tests

```bash
# Requires connected hardware
pytest tests/integration/ --hardware

# Dashboard tests
cd src/croom-dashboard/backend
npm test
```

## Documentation

Good documentation is crucial. Please update docs when:

- Adding new features
- Changing existing behavior
- Adding new configuration options
- Creating new APIs

### Documentation Structure

```
docs/
├── guides/          # User-facing guides
├── prd/             # Product requirements
├── roadmap/         # Development roadmap
├── api/             # API documentation
└── README.md        # Documentation index
```

### Writing Style

- Use clear, concise language
- Include code examples
- Add screenshots for UI features
- Keep docs up to date with code

## Project Structure

```
croom/
├── src/
│   ├── croom/                 # Core Python package
│   │   ├── core/               # Agent, config, services
│   │   ├── platform/           # Platform detection
│   │   ├── ai/                 # AI backends
│   │   ├── meeting/            # Meeting providers
│   │   ├── audio/              # Audio handling
│   │   └── video/              # Video handling
│   ├── croom-ui/              # Touch UI (Qt6/QML)
│   └── croom-dashboard/       # Management dashboard
│       ├── backend/            # Node.js API
│       └── frontend/           # React app
├── tests/                      # Test suite
├── docs/                       # Documentation
├── installer/                  # Installation scripts
└── packaging/                  # Distribution packaging
```

## Community

### Getting Help

- 💬 **GitHub Discussions** - Ask questions, share ideas
- 📧 **Mailing List** - croom-help@googlegroups.com
- 🐛 **Issue Tracker** - Report bugs, request features

### Recognition

Contributors are recognized in:
- README.md contributors section
- Release notes
- Annual contributor spotlight

### Maintainers

Current maintainers:
- [@amirhmoradi](https://github.com/amirhmoradi) - Project Lead

Want to become a maintainer? Consistent, quality contributions over time may lead to maintainer status.

---

## Thank You! 🙏

Every contribution matters, no matter how small. Thank you for helping make Croom better for everyone!

**Happy Contributing!** 🎥🍰
