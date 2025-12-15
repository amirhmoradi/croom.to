"""
Croom Touch UI Application.

Main application class that manages the Qt/QML interface.
"""

import os
import logging
import subprocess
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import QObject, Signal, Slot, Property, QUrl, QTimer
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtQuick import QQuickWindow

# Import croom core
try:
    from croom.core.config import Config, load_config
    from croom.platform.capabilities import CapabilityDetector
    CROOM_AVAILABLE = True
except ImportError:
    CROOM_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    """Audio device information."""
    name: str
    device_id: str
    is_default: bool = False
    channels: int = 2
    sample_rate: int = 48000


@dataclass
class VideoDevice:
    """Video device information."""
    name: str
    device_id: str
    is_default: bool = False
    resolutions: List[str] = field(default_factory=list)


@dataclass
class WifiNetwork:
    """WiFi network information."""
    ssid: str
    bssid: str
    frequency: float
    signalStrength: int
    secured: bool
    security: str


class MeetingController(QObject):
    """
    Controller for meeting operations exposed to QML.
    """

    # Signals
    meetingStateChanged = Signal(str)
    cameraStateChanged = Signal(bool)
    muteStateChanged = Signal(bool)
    errorOccurred = Signal(str)
    participantsChanged = Signal()
    recordingStateChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._meeting_state = "idle"
        self._camera_on = True
        self._muted = False
        self._meeting_service = None
        self._recording = False
        self._can_record = True
        self._participants = []
        self._recent_sip_endpoints = []

        # Platform availability flags
        self._google_meet_enabled = True
        self._teams_enabled = True
        self._zoom_enabled = True
        self._webex_enabled = False
        self._sip_enabled = False

    def set_meeting_service(self, service):
        """Set the meeting service instance."""
        self._meeting_service = service

    @Property(str, notify=meetingStateChanged)
    def meetingState(self):
        return self._meeting_state

    @Property(bool, notify=cameraStateChanged)
    def cameraOn(self):
        return self._camera_on

    @Property(bool, notify=muteStateChanged)
    def muted(self):
        return self._muted

    @Property(bool, notify=recordingStateChanged)
    def isRecording(self):
        return self._recording

    @Property(bool, constant=True)
    def canRecord(self):
        return self._can_record

    @Property("QVariantList", notify=participantsChanged)
    def participants(self):
        return self._participants

    @Property("QVariantList", constant=True)
    def recentSipEndpoints(self):
        return self._recent_sip_endpoints

    @Property(bool, constant=True)
    def googleMeetEnabled(self):
        return self._google_meet_enabled

    @Property(bool, constant=True)
    def teamsEnabled(self):
        return self._teams_enabled

    @Property(bool, constant=True)
    def zoomEnabled(self):
        return self._zoom_enabled

    @Property(bool, constant=True)
    def webexEnabled(self):
        return self._webex_enabled

    @Property(bool, constant=True)
    def sipEnabled(self):
        return self._sip_enabled

    @Slot(str)
    def joinMeeting(self, meeting_url: str):
        """Join a meeting by URL or code."""
        logger.info(f"Joining meeting: {meeting_url}")
        self._meeting_state = "joining"
        self.meetingStateChanged.emit(self._meeting_state)

        # Async call to meeting service
        if self._meeting_service:
            # Real meeting service call
            pass
        else:
            # Simulate success for development
            QTimer.singleShot(2000, lambda: self._on_meeting_joined())

    def _on_meeting_joined(self):
        self._meeting_state = "connected"
        self.meetingStateChanged.emit(self._meeting_state)

    @Slot(str)
    def startInstantMeeting(self, platform: str):
        """Start an instant meeting on the specified platform."""
        logger.info(f"Starting instant meeting on: {platform}")
        self._meeting_state = "starting"
        self.meetingStateChanged.emit(self._meeting_state)

        # Map platform to meeting URL
        platform_urls = {
            "google_meet": "https://meet.google.com/new",
            "teams": "https://teams.microsoft.com/l/meetup-join/new",
            "zoom": "https://zoom.us/start/webmeeting",
            "webex": "https://webex.com/meet",
            "jitsi": f"https://meet.jit.si/croom-{self._generate_meeting_id()}"
        }

        meeting_url = platform_urls.get(platform)
        if meeting_url:
            # Simulate starting meeting
            QTimer.singleShot(2000, lambda: self._on_meeting_joined())
        else:
            self._meeting_state = "idle"
            self.meetingStateChanged.emit(self._meeting_state)
            self.errorOccurred.emit(f"Unknown platform: {platform}")

    def _generate_meeting_id(self) -> str:
        """Generate a random meeting ID."""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    @Slot(str)
    def dialSipEndpoint(self, address: str):
        """Dial a SIP/H.323 endpoint."""
        logger.info(f"Dialing SIP endpoint: {address}")
        self._meeting_state = "dialing"
        self.meetingStateChanged.emit(self._meeting_state)

        # Add to recent endpoints
        if address not in self._recent_sip_endpoints:
            self._recent_sip_endpoints.insert(0, address)
            self._recent_sip_endpoints = self._recent_sip_endpoints[:10]  # Keep last 10

        # Simulate connection
        QTimer.singleShot(3000, lambda: self._on_meeting_joined())

    @Slot()
    def leaveMeeting(self):
        """Leave the current meeting."""
        logger.info("Leaving meeting")
        self._meeting_state = "idle"
        self._recording = False
        self.meetingStateChanged.emit(self._meeting_state)
        self.recordingStateChanged.emit(self._recording)

    @Slot()
    def toggleCamera(self):
        """Toggle camera on/off."""
        self._camera_on = not self._camera_on
        self.cameraStateChanged.emit(self._camera_on)
        logger.info(f"Camera: {'on' if self._camera_on else 'off'}")

    @Slot()
    def toggleMute(self):
        """Toggle microphone mute."""
        self._muted = not self._muted
        self.muteStateChanged.emit(self._muted)
        logger.info(f"Mute: {'on' if self._muted else 'off'}")

    @Slot()
    def toggleRecording(self):
        """Toggle meeting recording."""
        self._recording = not self._recording
        self.recordingStateChanged.emit(self._recording)
        logger.info(f"Recording: {'started' if self._recording else 'stopped'}")


class CalendarController(QObject):
    """
    Controller for calendar operations exposed to QML.
    """

    # Signals
    meetingsUpdated = Signal()
    upcomingMeetingChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._meetings = []
        self._upcoming_meeting = None

    @Property("QVariantList", notify=meetingsUpdated)
    def meetings(self):
        return self._meetings

    @Property("QVariant", notify=upcomingMeetingChanged)
    def upcomingMeeting(self):
        return self._upcoming_meeting

    @Slot()
    def refreshCalendar(self):
        """Refresh calendar data."""
        logger.info("Refreshing calendar")
        # TODO: Fetch from calendar service
        self.meetingsUpdated.emit()


class RoomController(QObject):
    """
    Controller for room status and settings exposed to QML.
    """

    # Signals
    roomNameChanged = Signal()
    occupancyChanged = Signal()
    aiStatusChanged = Signal()

    def __init__(self, config: Optional[Config] = None, parent=None):
        super().__init__(parent)
        self._config = config
        self._room_name = config.room.name if config else "Conference Room"
        self._occupancy = 0
        self._ai_enabled = config.ai.enabled if config else False

    @Property(str, notify=roomNameChanged)
    def roomName(self):
        return self._room_name

    @Property(int, notify=occupancyChanged)
    def occupancy(self):
        return self._occupancy

    @Property(bool, notify=aiStatusChanged)
    def aiEnabled(self):
        return self._ai_enabled

    def update_occupancy(self, count: int):
        """Update occupancy count from AI service."""
        if count != self._occupancy:
            self._occupancy = count
            self.occupancyChanged.emit()


class NetworkController(QObject):
    """
    Controller for network/WiFi operations exposed to QML.
    """

    # Signals
    networksChanged = Signal()
    connectionStatusChanged = Signal()
    isScanningChanged = Signal()
    connectionResult = Signal(bool, str)  # success, message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._available_networks: List[Dict] = []
        self._current_network: Optional[Dict] = None
        self._is_scanning = False
        self._is_connected = False
        self._connection_type = "none"  # "wifi", "ethernet", "none"
        self._ip_address = ""
        self._link_speed = ""

        # Initialize with mock data for development
        self._available_networks = [
            {"ssid": "CroomNet", "bssid": "00:11:22:33:44:55", "frequency": 5.0,
             "signalStrength": 85, "secured": True, "security": "WPA2"},
            {"ssid": "Guest-WiFi", "bssid": "00:11:22:33:44:56", "frequency": 2.4,
             "signalStrength": 70, "secured": True, "security": "WPA2"},
            {"ssid": "Conference_5G", "bssid": "00:11:22:33:44:57", "frequency": 5.0,
             "signalStrength": 60, "secured": True, "security": "WPA3"},
        ]

    @Property("QVariantList", notify=networksChanged)
    def availableNetworks(self):
        return self._available_networks

    @Property("QVariant", notify=connectionStatusChanged)
    def currentNetwork(self):
        return self._current_network

    @Property(bool, notify=isScanningChanged)
    def isScanning(self):
        return self._is_scanning

    @Property(bool, notify=connectionStatusChanged)
    def isConnected(self):
        return self._is_connected

    @Property(str, notify=connectionStatusChanged)
    def connectionType(self):
        return self._connection_type

    @Property(str, notify=connectionStatusChanged)
    def ipAddress(self):
        return self._ip_address

    @Property(str, notify=connectionStatusChanged)
    def linkSpeed(self):
        return self._link_speed

    @Slot()
    def scanNetworks(self):
        """Scan for available WiFi networks."""
        logger.info("Scanning for WiFi networks")
        self._is_scanning = True
        self.isScanningChanged.emit()

        # Simulate scan delay
        QTimer.singleShot(2000, self._complete_scan)

    def _complete_scan(self):
        """Complete network scan."""
        self._is_scanning = False
        self.isScanningChanged.emit()
        self.networksChanged.emit()

    @Slot(str, str)
    def connectToNetwork(self, ssid: str, password: str):
        """Connect to a WiFi network."""
        logger.info(f"Connecting to network: {ssid}")

        # Find network
        network = next((n for n in self._available_networks if n["ssid"] == ssid), None)
        if not network:
            self.connectionResult.emit(False, "Network not found")
            return

        # Simulate connection
        QTimer.singleShot(3000, lambda: self._on_connected(network))

    def _on_connected(self, network: Dict):
        """Handle successful connection."""
        self._current_network = network
        self._is_connected = True
        self._connection_type = "wifi"
        self._ip_address = "192.168.1.100"
        self._link_speed = "866 Mbps"
        self.connectionStatusChanged.emit()
        self.connectionResult.emit(True, "Connected successfully")

    @Slot()
    def disconnect(self):
        """Disconnect from current network."""
        logger.info("Disconnecting from network")
        self._current_network = None
        self._is_connected = False
        self._connection_type = "none"
        self._ip_address = ""
        self._link_speed = ""
        self.connectionStatusChanged.emit()

    @Slot(str)
    def forgetNetwork(self, ssid: str):
        """Forget a saved network."""
        logger.info(f"Forgetting network: {ssid}")
        if self._current_network and self._current_network.get("ssid") == ssid:
            self.disconnect()

    @Slot("QVariant")
    def saveAdvancedSettings(self, settings: Dict):
        """Save advanced network settings."""
        logger.info(f"Saving advanced settings: {settings}")


class AudioVideoController(QObject):
    """
    Controller for audio/video device management exposed to QML.
    """

    # Signals
    devicesChanged = Signal()
    micLevelChanged = Signal()
    previewStateChanged = Signal()
    testAudioStateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cameras: List[Dict] = []
        self._microphones: List[Dict] = []
        self._speakers: List[Dict] = []
        self._selected_camera_index = 0
        self._selected_mic_index = 0
        self._selected_speaker_index = 0
        self._mic_level = 0.0
        self._mic_volume = 80
        self._speaker_volume = 70
        self._preview_active = False
        self._is_testing_audio = False
        self._resolution_index = 1  # 720p default
        self._fps_index = 0  # 30fps default
        self._echo_cancellation = True
        self._noise_suppression = True
        self._auto_gain_control = True

        # Initialize with mock devices
        self._cameras = [
            {"name": "USB HD Webcam", "device_id": "/dev/video0"},
            {"name": "Built-in Camera", "device_id": "/dev/video1"},
        ]
        self._microphones = [
            {"name": "USB Microphone", "device_id": "hw:1,0"},
            {"name": "Built-in Mic", "device_id": "hw:0,0"},
        ]
        self._speakers = [
            {"name": "HDMI Audio", "device_id": "hdmi"},
            {"name": "USB Speaker", "device_id": "usb-audio"},
            {"name": "3.5mm Jack", "device_id": "analog"},
        ]

        # Start mic level monitor
        self._mic_timer = QTimer()
        self._mic_timer.timeout.connect(self._update_mic_level)
        self._mic_timer.start(100)

    @Property("QVariantList", notify=devicesChanged)
    def cameras(self):
        return self._cameras

    @Property("QVariantList", notify=devicesChanged)
    def microphones(self):
        return self._microphones

    @Property("QVariantList", notify=devicesChanged)
    def speakers(self):
        return self._speakers

    @Property(int, notify=devicesChanged)
    def selectedCameraIndex(self):
        return self._selected_camera_index

    @Property(int, notify=devicesChanged)
    def selectedMicIndex(self):
        return self._selected_mic_index

    @Property(int, notify=devicesChanged)
    def selectedSpeakerIndex(self):
        return self._selected_speaker_index

    @Property(float, notify=micLevelChanged)
    def micLevel(self):
        return self._mic_level

    @Property(int, notify=devicesChanged)
    def micVolume(self):
        return self._mic_volume

    @Property(int, notify=devicesChanged)
    def speakerVolume(self):
        return self._speaker_volume

    @Property(bool, notify=previewStateChanged)
    def previewActive(self):
        return self._preview_active

    @Property(bool, notify=testAudioStateChanged)
    def isTestingAudio(self):
        return self._is_testing_audio

    @Property(int, notify=devicesChanged)
    def resolutionIndex(self):
        return self._resolution_index

    @Property(int, notify=devicesChanged)
    def fpsIndex(self):
        return self._fps_index

    @Property(bool, notify=devicesChanged)
    def echoCancellation(self):
        return self._echo_cancellation

    @Property(bool, notify=devicesChanged)
    def noiseSuppression(self):
        return self._noise_suppression

    @Property(bool, notify=devicesChanged)
    def autoGainControl(self):
        return self._auto_gain_control

    def _update_mic_level(self):
        """Simulate mic level changes."""
        import random
        # Simulate audio levels with some noise
        base_level = 0.3 + random.random() * 0.4
        self._mic_level = min(1.0, base_level * (self._mic_volume / 100))
        self.micLevelChanged.emit()

    @Slot(int)
    def setCamera(self, index: int):
        """Select camera by index."""
        if 0 <= index < len(self._cameras):
            self._selected_camera_index = index
            self.devicesChanged.emit()
            logger.info(f"Selected camera: {self._cameras[index]['name']}")

    @Slot(int)
    def setMicrophone(self, index: int):
        """Select microphone by index."""
        if 0 <= index < len(self._microphones):
            self._selected_mic_index = index
            self.devicesChanged.emit()
            logger.info(f"Selected microphone: {self._microphones[index]['name']}")

    @Slot(int)
    def setSpeaker(self, index: int):
        """Select speaker by index."""
        if 0 <= index < len(self._speakers):
            self._selected_speaker_index = index
            self.devicesChanged.emit()
            logger.info(f"Selected speaker: {self._speakers[index]['name']}")

    @Slot(int)
    def setMicVolume(self, volume: int):
        """Set microphone volume."""
        self._mic_volume = max(0, min(100, volume))
        self.devicesChanged.emit()

    @Slot(int)
    def setSpeakerVolume(self, volume: int):
        """Set speaker volume."""
        self._speaker_volume = max(0, min(100, volume))
        self.devicesChanged.emit()

    @Slot(int)
    def setResolution(self, index: int):
        """Set video resolution."""
        self._resolution_index = index
        self.devicesChanged.emit()

    @Slot(int)
    def setFrameRate(self, index: int):
        """Set video frame rate."""
        self._fps_index = index
        self.devicesChanged.emit()

    @Slot(bool)
    def setEchoCancellation(self, enabled: bool):
        """Enable/disable echo cancellation."""
        self._echo_cancellation = enabled
        self.devicesChanged.emit()

    @Slot(bool)
    def setNoiseSuppression(self, enabled: bool):
        """Enable/disable noise suppression."""
        self._noise_suppression = enabled
        self.devicesChanged.emit()

    @Slot(bool)
    def setAutoGainControl(self, enabled: bool):
        """Enable/disable auto gain control."""
        self._auto_gain_control = enabled
        self.devicesChanged.emit()

    @Slot()
    def togglePreview(self):
        """Toggle camera preview."""
        self._preview_active = not self._preview_active
        self.previewStateChanged.emit()
        logger.info(f"Camera preview: {'active' if self._preview_active else 'stopped'}")

    @Slot()
    def stopPreview(self):
        """Stop camera preview."""
        self._preview_active = False
        self.previewStateChanged.emit()

    @Slot()
    def testSpeaker(self):
        """Play test sound through speaker."""
        if not self._is_testing_audio:
            self._is_testing_audio = True
            self.testAudioStateChanged.emit()
            logger.info("Playing test sound")
            # Simulate test duration
            QTimer.singleShot(3000, self._stop_audio_test)

    def _stop_audio_test(self):
        """Stop audio test."""
        self._is_testing_audio = False
        self.testAudioStateChanged.emit()

    @Slot()
    def refreshDevices(self):
        """Refresh list of audio/video devices."""
        logger.info("Refreshing audio/video devices")
        # In real implementation, would enumerate actual devices
        self.devicesChanged.emit()

    @Slot()
    def resetToDefaults(self):
        """Reset all settings to defaults."""
        self._selected_camera_index = 0
        self._selected_mic_index = 0
        self._selected_speaker_index = 0
        self._mic_volume = 80
        self._speaker_volume = 70
        self._resolution_index = 1
        self._fps_index = 0
        self._echo_cancellation = True
        self._noise_suppression = True
        self._auto_gain_control = True
        self.devicesChanged.emit()
        logger.info("Reset audio/video settings to defaults")


class SettingsController(QObject):
    """
    Controller for settings and PIN protection exposed to QML.
    """

    # Signals
    pinVerified = Signal(bool)
    settingsChanged = Signal()

    def __init__(self, config: Optional[Config] = None, parent=None):
        super().__init__(parent)
        self._config = config
        self._admin_pin = "1234"  # Default PIN
        self._is_admin_mode = False

    @Property(bool, notify=settingsChanged)
    def isAdminMode(self):
        return self._is_admin_mode

    @Slot(str, result=bool)
    def verifyPin(self, pin: str) -> bool:
        """Verify admin PIN."""
        if pin == self._admin_pin:
            self._is_admin_mode = True
            self.pinVerified.emit(True)
            self.settingsChanged.emit()
            return True
        else:
            self.pinVerified.emit(False)
            return False

    @Slot(str, str, result=bool)
    def changePin(self, old_pin: str, new_pin: str) -> bool:
        """Change admin PIN."""
        if old_pin == self._admin_pin:
            self._admin_pin = new_pin
            logger.info("Admin PIN changed")
            return True
        return False

    @Slot()
    def exitAdminMode(self):
        """Exit admin mode."""
        self._is_admin_mode = False
        self.settingsChanged.emit()


class CroomUI:
    """
    Main Croom Touch UI application.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        fullscreen: bool = True,
        debug: bool = False
    ):
        self.config = load_config(config_path) if CROOM_AVAILABLE else None
        self.fullscreen = fullscreen
        self.debug = debug

        # Create QML engine
        self.engine = QQmlApplicationEngine()

        # Create controllers
        self.meeting_controller = MeetingController()
        self.calendar_controller = CalendarController()
        self.room_controller = RoomController(self.config)
        self.network_controller = NetworkController()
        self.av_controller = AudioVideoController()
        self.settings_controller = SettingsController(self.config)

        # Expose controllers to QML
        self.engine.rootContext().setContextProperty("meetingController", self.meeting_controller)
        self.engine.rootContext().setContextProperty("calendarController", self.calendar_controller)
        self.engine.rootContext().setContextProperty("roomController", self.room_controller)
        self.engine.rootContext().setContextProperty("networkController", self.network_controller)
        self.engine.rootContext().setContextProperty("avController", self.av_controller)
        self.engine.rootContext().setContextProperty("settingsController", self.settings_controller)

        # Set debug mode
        self.engine.rootContext().setContextProperty("debugMode", self.debug)

        # Find QML directory
        self.qml_dir = self._find_qml_dir()
        logger.info(f"QML directory: {self.qml_dir}")

    def _find_qml_dir(self) -> Path:
        """Find the QML directory."""
        # Check relative to this file
        base = Path(__file__).parent.parent
        qml_dir = base / "qml"
        if qml_dir.exists():
            return qml_dir

        # Check installed location
        import sys
        for path in sys.path:
            qml_dir = Path(path) / "croom_ui" / "qml"
            if qml_dir.exists():
                return qml_dir

        # Fallback to creating empty qml dir
        qml_dir = base / "qml"
        qml_dir.mkdir(exist_ok=True)
        return qml_dir

    def show(self):
        """Show the main window."""
        # Load main QML file
        main_qml = self.qml_dir / "main.qml"

        if main_qml.exists():
            self.engine.load(QUrl.fromLocalFile(str(main_qml)))
        else:
            logger.warning(f"Main QML file not found: {main_qml}")
            self._create_fallback_qml()
            self.engine.load(QUrl.fromLocalFile(str(main_qml)))

        if not self.engine.rootObjects():
            logger.error("Failed to load QML")
            return

        # Configure window
        root = self.engine.rootObjects()[0]
        if isinstance(root, QQuickWindow):
            if self.fullscreen:
                root.showFullScreen()
            else:
                root.show()

    def _create_fallback_qml(self):
        """Create a minimal fallback QML if main.qml doesn't exist."""
        main_qml = self.qml_dir / "main.qml"
        fallback = '''
import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15

Window {
    id: window
    width: 1024
    height: 600
    visible: true
    title: "Croom Room Controller"
    color: "#1a1a2e"

    Text {
        anchors.centerIn: parent
        text: "Croom Touch UI"
        color: "white"
        font.pixelSize: 48
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.verticalCenter
        anchors.topMargin: 60
        text: "QML files not found. Please install the UI package."
        color: "#888"
        font.pixelSize: 18
    }
}
'''
        main_qml.write_text(fallback)
