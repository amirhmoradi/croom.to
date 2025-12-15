"""
PiMeet Touch UI Application.

Main application class that manages the Qt/QML interface.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import QObject, Signal, Slot, Property, QUrl, QTimer
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtQuick import QQuickWindow

# Import pimeet core
try:
    from pimeet.core.config import Config, load_config
    from pimeet.platform.capabilities import CapabilityDetector
    PIMEET_AVAILABLE = True
except ImportError:
    PIMEET_AVAILABLE = False

logger = logging.getLogger(__name__)


class MeetingController(QObject):
    """
    Controller for meeting operations exposed to QML.
    """

    # Signals
    meetingStateChanged = Signal(str)
    cameraStateChanged = Signal(bool)
    muteStateChanged = Signal(bool)
    errorOccurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._meeting_state = "idle"
        self._camera_on = True
        self._muted = False
        self._meeting_service = None

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

    @Slot(str)
    def joinMeeting(self, meeting_url: str):
        """Join a meeting by URL or code."""
        logger.info(f"Joining meeting: {meeting_url}")
        self._meeting_state = "joining"
        self.meetingStateChanged.emit(self._meeting_state)

        # TODO: Async call to meeting service
        # For now, simulate success
        QTimer.singleShot(2000, lambda: self._on_meeting_joined())

    def _on_meeting_joined(self):
        self._meeting_state = "connected"
        self.meetingStateChanged.emit(self._meeting_state)

    @Slot()
    def leaveMeeting(self):
        """Leave the current meeting."""
        logger.info("Leaving meeting")
        self._meeting_state = "idle"
        self.meetingStateChanged.emit(self._meeting_state)

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


class PiMeetUI:
    """
    Main PiMeet Touch UI application.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        fullscreen: bool = True,
        debug: bool = False
    ):
        self.config = load_config(config_path) if PIMEET_AVAILABLE else None
        self.fullscreen = fullscreen
        self.debug = debug

        # Create QML engine
        self.engine = QQmlApplicationEngine()

        # Create controllers
        self.meeting_controller = MeetingController()
        self.calendar_controller = CalendarController()
        self.room_controller = RoomController(self.config)

        # Expose controllers to QML
        self.engine.rootContext().setContextProperty("meetingController", self.meeting_controller)
        self.engine.rootContext().setContextProperty("calendarController", self.calendar_controller)
        self.engine.rootContext().setContextProperty("roomController", self.room_controller)

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
            qml_dir = Path(path) / "pimeet_ui" / "qml"
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
    title: "PiMeet Room Controller"
    color: "#1a1a2e"

    Text {
        anchors.centerIn: parent
        text: "PiMeet Touch UI"
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
