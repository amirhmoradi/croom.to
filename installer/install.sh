#!/bin/bash
#
# Croom Installer
#
# Non-destructive installation on existing Raspberry Pi OS
# Supports: Bookworm, Trixie
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CROOM_VERSION="2.0.0-dev"
INSTALL_DIR="/opt/croom"
CONFIG_DIR="/etc/croom"
DATA_DIR="/var/lib/croom"
LOG_DIR="/var/log/croom"
CROOM_USER="croom"

# Log function
log() {
    echo -e "${GREEN}[Croom]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[Warning]${NC} $1"
}

error() {
    echo -e "${RED}[Error]${NC} $1"
    exit 1
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

# Check platform compatibility
check_platform() {
    log "Checking platform compatibility..."

    # Check architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" != "aarch64" && "$ARCH" != "x86_64" ]]; then
        error "Unsupported architecture: $ARCH (need aarch64 or x86_64)"
    fi

    # Check OS
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        log "Detected: $PRETTY_NAME"

        case "$VERSION_CODENAME" in
            bookworm|trixie|jammy|noble)
                log "OS version supported"
                ;;
            *)
                warn "OS version '$VERSION_CODENAME' not officially supported"
                ;;
        esac
    else
        warn "Could not detect OS version"
    fi

    # Check if Raspberry Pi
    if [[ -f /proc/device-tree/model ]]; then
        MODEL=$(cat /proc/device-tree/model | tr -d '\0')
        log "Hardware: $MODEL"
    fi
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."

    apt-get update

    # Core dependencies
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        chromium-browser \
        pulseaudio \
        v4l-utils \
        libcamera-apps \
        cec-utils \
        git \
        curl \
        wget

    # Qt dependencies for Touch UI
    apt-get install -y \
        python3-pyside6.qtcore \
        python3-pyside6.qtgui \
        python3-pyside6.qtwidgets \
        python3-pyside6.qtqml \
        python3-pyside6.qtquick \
        qml6-module-qtquick \
        qml6-module-qtquick-controls \
        qml6-module-qtquick-layouts \
        qml6-module-qtquick-window || warn "Some Qt packages not available, Touch UI may not work"

    # Optional: AI acceleration support
    if [[ -d /dev/hailo* ]] || lsusb | grep -q "1a6e:089a\|18d1:9302"; then
        log "AI accelerator detected, installing support libraries..."
        # Hailo support would be installed via separate repo
        # Coral support via google-coral packages
    fi

    log "Dependencies installed"
}

# Create croom user
create_user() {
    log "Creating croom user..."

    if id "$CROOM_USER" &>/dev/null; then
        log "User $CROOM_USER already exists"
    else
        useradd -r -s /bin/false -d "$INSTALL_DIR" "$CROOM_USER"
        log "User $CROOM_USER created"
    fi

    # Add to required groups
    usermod -a -G video,audio,input,dialout,gpio "$CROOM_USER" 2>/dev/null || true
}

# Create directory structure
create_directories() {
    log "Creating directories..."

    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$INSTALL_DIR/models"

    chown -R "$CROOM_USER:$CROOM_USER" "$INSTALL_DIR"
    chown -R "$CROOM_USER:$CROOM_USER" "$DATA_DIR"
    chown -R "$CROOM_USER:$CROOM_USER" "$LOG_DIR"
}

# Install Croom Python package
install_croom() {
    log "Installing Croom..."

    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"

    # Install package
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install croom || {
        # If package not on PyPI, install from source
        log "Installing from source..."
        "$INSTALL_DIR/venv/bin/pip" install /usr/local/src/croom 2>/dev/null || \
        "$INSTALL_DIR/venv/bin/pip" install git+https://github.com/your-org/croom.git
    }

    # Install browser automation
    "$INSTALL_DIR/venv/bin/pip" install playwright
    "$INSTALL_DIR/venv/bin/playwright" install chromium

    log "Croom installed"
}

# Create default configuration
create_config() {
    log "Creating configuration..."

    if [[ -f "$CONFIG_DIR/config.yaml" ]]; then
        log "Configuration already exists, skipping"
        return
    fi

    cat > "$CONFIG_DIR/config.yaml" << 'EOF'
# Croom Configuration
version: 2

room:
  name: "Conference Room"
  location: ""
  timezone: "UTC"

meeting:
  platforms:
    - google_meet
    - teams
    - zoom
  default_platform: auto
  join_early_minutes: 1
  auto_leave: true
  camera_default_on: true
  mic_default_on: true

calendar:
  providers:
    - google
    - microsoft
  sync_interval_seconds: 60

ai:
  enabled: true
  backend: auto
  person_detection: true
  noise_reduction: true
  echo_cancellation: true
  auto_framing: true
  occupancy_counting: true
  speaker_detection: false
  hand_raise_detection: false
  privacy_mode: false

audio:
  backend: auto
  input_device: auto
  output_device: auto
  noise_reduction_level: medium
  echo_cancellation: true

video:
  backend: auto
  device: auto
  resolution: 1080p
  framerate: 30

display:
  backend: auto
  power_on_boot: true
  power_off_shutdown: true
  touch_enabled: true

dashboard:
  enabled: true
  url: ""
  enrollment_token: ""
  heartbeat_interval_seconds: 30
  metrics_interval_seconds: 60

updates:
  auto_check: true
  auto_install: false
  check_interval_hours: 24
  channel: stable

security:
  admin_pin: ""
  ssh_enabled: true
  require_encryption: true
EOF

    chown "$CROOM_USER:$CROOM_USER" "$CONFIG_DIR/config.yaml"
    chmod 640 "$CONFIG_DIR/config.yaml"

    log "Configuration created at $CONFIG_DIR/config.yaml"
}

# Create systemd service
create_service() {
    log "Creating systemd service..."

    cat > /etc/systemd/system/croom.service << EOF
[Unit]
Description=Croom Conference Room Agent
After=network-online.target pulseaudio.service
Wants=network-online.target

[Service]
Type=simple
User=$CROOM_USER
Group=$CROOM_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python -m croom.core.agent -c $CONFIG_DIR/config.yaml
Restart=always
RestartSec=10
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000

[Install]
WantedBy=multi-user.target
EOF

    # Touch UI service (optional)
    cat > /etc/systemd/system/croom-ui.service << EOF
[Unit]
Description=Croom Touch UI
After=croom.service
Wants=croom.service

[Service]
Type=simple
User=$CROOM_USER
Group=$CROOM_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python -m croom_ui.main -c $CONFIG_DIR/config.yaml --fullscreen
Restart=always
RestartSec=10
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=QT_QPA_PLATFORM=eglfs

[Install]
WantedBy=graphical.target
EOF

    systemctl daemon-reload
    log "Systemd services created"
}

# Enable and start services
enable_services() {
    log "Enabling services..."

    systemctl enable croom.service

    # Only enable UI service if touch display is detected
    if [[ -e /dev/input/touchscreen* ]] || [[ "$ENABLE_UI" == "yes" ]]; then
        systemctl enable croom-ui.service
        log "Touch UI service enabled"
    fi
}

# Print completion message
print_completion() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Croom Installation Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Version: $CROOM_VERSION"
    echo "Install directory: $INSTALL_DIR"
    echo "Configuration: $CONFIG_DIR/config.yaml"
    echo ""
    echo "Next steps:"
    echo "1. Edit configuration: sudo nano $CONFIG_DIR/config.yaml"
    echo "2. Start service: sudo systemctl start croom"
    echo "3. Check status: sudo systemctl status croom"
    echo "4. View logs: sudo journalctl -u croom -f"
    echo ""
    echo "To connect to management dashboard:"
    echo "1. Get enrollment token from dashboard"
    echo "2. Add to config: dashboard.enrollment_token"
    echo "3. Restart: sudo systemctl restart croom"
    echo ""
}

# Main installation flow
main() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Croom Installer v$CROOM_VERSION${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    check_root
    check_platform
    create_user
    create_directories
    install_dependencies
    install_croom
    create_config
    create_service
    enable_services
    print_completion
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --enable-ui)
            ENABLE_UI="yes"
            shift
            ;;
        --no-service)
            NO_SERVICE="yes"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --enable-ui     Enable Touch UI service"
            echo "  --no-service    Don't create systemd services"
            echo "  --help          Show this help"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

main
