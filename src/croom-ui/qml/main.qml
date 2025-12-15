import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "screens"
import "components"

Window {
    id: mainWindow
    width: 1024
    height: 600
    visible: true
    title: roomController.roomName + " - Croom"
    color: Theme.backgroundColor

    // Theme singleton
    QtObject {
        id: Theme
        // Dark theme colors
        readonly property color backgroundColor: "#1a1a2e"
        readonly property color surfaceColor: "#16213e"
        readonly property color primaryColor: "#0f3460"
        readonly property color accentColor: "#e94560"
        readonly property color textColor: "#ffffff"
        readonly property color textSecondary: "#a0a0a0"
        readonly property color successColor: "#4caf50"
        readonly property color warningColor: "#ff9800"
        readonly property color errorColor: "#f44336"

        // Typography
        readonly property int fontSizeSmall: 14
        readonly property int fontSizeMedium: 18
        readonly property int fontSizeLarge: 24
        readonly property int fontSizeXLarge: 36
        readonly property int fontSizeHuge: 48

        // Spacing
        readonly property int spacingSmall: 8
        readonly property int spacingMedium: 16
        readonly property int spacingLarge: 24
        readonly property int spacingXLarge: 32

        // Border radius
        readonly property int radiusSmall: 8
        readonly property int radiusMedium: 12
        readonly property int radiusLarge: 16
    }

    // Main stack view for navigation
    StackView {
        id: stackView
        anchors.fill: parent
        initialItem: homeScreen

        // Transition animations
        pushEnter: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 0
                to: 1
                duration: 200
            }
        }
        pushExit: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 1
                to: 0
                duration: 200
            }
        }
        popEnter: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 0
                to: 1
                duration: 200
            }
        }
        popExit: Transition {
            PropertyAnimation {
                property: "opacity"
                from: 1
                to: 0
                duration: 200
            }
        }
    }

    // Screens
    Component {
        id: homeScreen
        HomeScreen {
            onJoinMeetingRequested: stackView.push(joinMeetingScreen)
            onSettingsRequested: stackView.push(settingsScreen)
            onCalendarRequested: stackView.push(calendarScreen)
        }
    }

    Component {
        id: joinMeetingScreen
        JoinMeetingScreen {
            onBackRequested: stackView.pop()
            onMeetingJoined: stackView.replace(inMeetingScreen)
        }
    }

    Component {
        id: inMeetingScreen
        InMeetingScreen {
            onMeetingEnded: stackView.replace(homeScreen)
        }
    }

    Component {
        id: calendarScreen
        CalendarScreen {
            onBackRequested: stackView.pop()
            onMeetingSelected: function(meetingUrl) {
                stackView.push(joinMeetingScreen, { prefillUrl: meetingUrl })
            }
        }
    }

    Component {
        id: settingsScreen
        SettingsScreen {
            onBackRequested: stackView.pop()
        }
    }

    // Handle meeting state changes
    Connections {
        target: meetingController
        function onMeetingStateChanged(state) {
            if (state === "connected" && stackView.currentItem.objectName !== "inMeetingScreen") {
                stackView.replace(inMeetingScreen)
            } else if (state === "idle" && stackView.currentItem.objectName === "inMeetingScreen") {
                stackView.replace(homeScreen)
            }
        }
    }

    // Status bar at bottom
    Rectangle {
        id: statusBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 40
        color: Theme.surfaceColor

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spacingMedium
            anchors.rightMargin: Theme.spacingMedium
            spacing: Theme.spacingLarge

            // Room name
            Text {
                text: roomController.roomName
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSmall
            }

            // Occupancy (if AI enabled)
            Text {
                visible: roomController.aiEnabled
                text: "👥 " + roomController.occupancy + " people"
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSizeSmall
            }

            Item { Layout.fillWidth: true }

            // Time
            Text {
                id: clockText
                color: Theme.textColor
                font.pixelSize: Theme.fontSizeSmall
                font.bold: true

                Timer {
                    interval: 1000
                    running: true
                    repeat: true
                    triggeredOnStart: true
                    onTriggered: {
                        var now = new Date()
                        clockText.text = Qt.formatTime(now, "hh:mm")
                    }
                }
            }
        }
    }
}
