import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

/**
 * QuickMeetScreen.qml - Start an instant meeting
 *
 * Allows users to quickly start ad-hoc meetings on various platforms
 * without requiring a pre-scheduled meeting URL.
 */
Item {
    id: quickMeetScreen
    objectName: "quickMeetScreen"

    signal backRequested()
    signal meetingStarted(string platform, string meetingUrl)

    // Back button
    Rectangle {
        id: backButton
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 24
        width: 60
        height: 60
        color: "#16213e"
        radius: 30

        Text {
            anchors.centerIn: parent
            text: "\u2190"
            color: "#ffffff"
            font.pixelSize: 24
        }

        MouseArea {
            anchors.fill: parent
            onClicked: quickMeetScreen.backRequested()
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 32
        width: Math.min(700, parent.width - 48)

        // Title
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Start Instant Meeting"
            color: "#ffffff"
            font.pixelSize: 36
            font.bold: true
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Select a platform to start a new meeting"
            color: "#a0a0a0"
            font.pixelSize: 18
        }

        // Platform selection grid
        GridLayout {
            Layout.alignment: Qt.AlignHCenter
            columns: 3
            columnSpacing: 24
            rowSpacing: 24

            // Google Meet
            PlatformCard {
                platformName: "Google Meet"
                platformIcon: "G"
                platformColor: "#4285f4"
                description: "Start a Google Meet session"
                enabled: meetingController.googleMeetEnabled
                onClicked: startMeeting("google_meet")
            }

            // Microsoft Teams
            PlatformCard {
                platformName: "Microsoft Teams"
                platformIcon: "T"
                platformColor: "#6264a7"
                description: "Start a Teams meeting"
                enabled: meetingController.teamsEnabled
                onClicked: startMeeting("teams")
            }

            // Zoom
            PlatformCard {
                platformName: "Zoom"
                platformIcon: "Z"
                platformColor: "#2d8cff"
                description: "Start a Zoom meeting"
                enabled: meetingController.zoomEnabled
                onClicked: startMeeting("zoom")
            }

            // Webex
            PlatformCard {
                platformName: "Cisco Webex"
                platformIcon: "W"
                platformColor: "#00bceb"
                description: "Start a Webex meeting"
                enabled: meetingController.webexEnabled
                onClicked: startMeeting("webex")
            }

            // Jitsi (self-hosted option)
            PlatformCard {
                platformName: "Jitsi Meet"
                platformIcon: "J"
                platformColor: "#97979a"
                description: "Start a Jitsi meeting"
                enabled: true
                onClicked: startMeeting("jitsi")
            }

            // Generic SIP/H.323
            PlatformCard {
                platformName: "SIP/H.323"
                platformIcon: "SIP"
                platformColor: "#666666"
                description: "Direct dial SIP endpoint"
                enabled: meetingController.sipEnabled
                onClicked: showSipDialog()
            }
        }

        // Status indicator when starting
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 400
            Layout.preferredHeight: 60
            color: "#16213e"
            radius: 12
            visible: meetingController.meetingState === "starting"

            Row {
                anchors.centerIn: parent
                spacing: 16

                // Loading spinner
                Rectangle {
                    width: 32
                    height: 32
                    radius: 16
                    color: "transparent"
                    border.color: "#e94560"
                    border.width: 3

                    Rectangle {
                        width: parent.width / 2
                        height: parent.height
                        color: "#e94560"
                        radius: parent.radius
                        x: -width / 2
                    }

                    RotationAnimation on rotation {
                        from: 0
                        to: 360
                        duration: 1000
                        loops: Animation.Infinite
                        running: meetingController.meetingState === "starting"
                    }
                }

                Text {
                    text: "Starting meeting..."
                    color: "#ffffff"
                    font.pixelSize: 18
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        // Pre-meeting settings
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 500
            Layout.preferredHeight: preJoinColumn.height + 32
            color: "#16213e"
            radius: 12

            Column {
                id: preJoinColumn
                anchors.centerIn: parent
                width: parent.width - 32
                spacing: 16

                Text {
                    text: "Pre-join Settings"
                    color: "#a0a0a0"
                    font.pixelSize: 14
                    font.bold: true
                }

                // Camera/mic settings row
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 48

                    // Camera toggle
                    Column {
                        spacing: 8

                        Rectangle {
                            width: 70
                            height: 70
                            radius: 35
                            color: meetingController.cameraOn ? "#4caf50" : "#666"
                            anchors.horizontalCenter: parent.horizontalCenter

                            Text {
                                anchors.centerIn: parent
                                text: meetingController.cameraOn ? "\ud83d\udcf9" : "\ud83d\udeab"
                                font.pixelSize: 28
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: meetingController.toggleCamera()
                            }
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: meetingController.cameraOn ? "Camera On" : "Camera Off"
                            color: "#a0a0a0"
                            font.pixelSize: 14
                        }
                    }

                    // Mic toggle
                    Column {
                        spacing: 8

                        Rectangle {
                            width: 70
                            height: 70
                            radius: 35
                            color: !meetingController.muted ? "#4caf50" : "#f44336"
                            anchors.horizontalCenter: parent.horizontalCenter

                            Text {
                                anchors.centerIn: parent
                                text: !meetingController.muted ? "\ud83c\udfa4" : "\ud83d\udd07"
                                font.pixelSize: 28
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: meetingController.toggleMute()
                            }
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: !meetingController.muted ? "Mic On" : "Mic Off"
                            color: "#a0a0a0"
                            font.pixelSize: 14
                        }
                    }
                }
            }
        }
    }

    // SIP dial dialog
    Popup {
        id: sipDialog
        modal: true
        anchors.centerIn: parent
        width: 500
        height: 350
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: "#1a1a2e"
            radius: 16
            border.color: "#333"
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: 20

            Text {
                Layout.fillWidth: true
                text: "Dial SIP/H.323 Endpoint"
                color: "#ffffff"
                font.pixelSize: 22
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
            }

            TextField {
                id: sipAddressInput
                Layout.fillWidth: true
                Layout.preferredHeight: 50
                placeholderText: "sip:room@example.com or h323:address"
                placeholderTextColor: "#666"
                color: "#ffffff"
                font.pixelSize: 16

                background: Rectangle {
                    color: "#16213e"
                    radius: 8
                    border.color: sipAddressInput.focus ? "#e94560" : "#333"
                    border.width: 2
                }
            }

            // Preset endpoints
            Text {
                text: "Recent endpoints:"
                color: "#a0a0a0"
                font.pixelSize: 14
            }

            ListView {
                Layout.fillWidth: true
                Layout.preferredHeight: 80
                clip: true
                orientation: ListView.Horizontal
                spacing: 8

                model: meetingController.recentSipEndpoints || []

                delegate: Rectangle {
                    width: 150
                    height: 36
                    radius: 18
                    color: "#0f3460"

                    Text {
                        anchors.centerIn: parent
                        text: modelData
                        color: "#ffffff"
                        font.pixelSize: 12
                        elide: Text.ElideMiddle
                        width: parent.width - 16
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: sipAddressInput.text = modelData
                    }
                }
            }

            // Action buttons
            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    height: 50
                    radius: 12
                    color: "transparent"
                    border.color: "#666"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "Cancel"
                        color: "#a0a0a0"
                        font.pixelSize: 16
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: sipDialog.close()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 50
                    radius: 12
                    color: sipAddressInput.text.length > 0 ? "#e94560" : "#666"

                    Text {
                        anchors.centerIn: parent
                        text: "Dial"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: sipAddressInput.text.length > 0
                        onClicked: {
                            meetingController.dialSipEndpoint(sipAddressInput.text)
                            sipDialog.close()
                        }
                    }
                }
            }
        }
    }

    // Platform card component
    component PlatformCard: Rectangle {
        property string platformName: ""
        property string platformIcon: ""
        property color platformColor: "#666"
        property string description: ""
        property bool enabled: true

        signal clicked()

        width: 180
        height: 180
        radius: 16
        color: enabled ? (mouseArea.containsMouse ? Qt.lighter("#16213e", 1.2) : "#16213e") : "#0d0d1a"
        border.color: enabled ? platformColor : "#333"
        border.width: mouseArea.containsMouse && enabled ? 3 : 2
        opacity: enabled ? 1.0 : 0.5

        Behavior on border.width {
            NumberAnimation { duration: 150 }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            enabled: parent.enabled
            onClicked: parent.clicked()
            onPressed: parent.scale = 0.95
            onReleased: parent.scale = 1.0
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ForbiddenCursor
        }

        Behavior on scale {
            NumberAnimation { duration: 100 }
        }

        Column {
            anchors.centerIn: parent
            spacing: 12

            // Platform icon/logo
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 60
                height: 60
                radius: 30
                color: platformColor

                Text {
                    anchors.centerIn: parent
                    text: platformIcon
                    color: "#ffffff"
                    font.pixelSize: platformIcon.length > 1 ? 18 : 28
                    font.bold: true
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: platformName
                color: "#ffffff"
                font.pixelSize: 16
                font.bold: true
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: description
                color: "#a0a0a0"
                font.pixelSize: 11
                width: 160
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }

        // Disabled overlay
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            visible: !enabled

            Text {
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 8
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Not configured"
                color: "#666"
                font.pixelSize: 10
            }
        }
    }

    function startMeeting(platform) {
        meetingController.startInstantMeeting(platform)
    }

    function showSipDialog() {
        sipAddressInput.text = ""
        sipDialog.open()
    }

    // Handle meeting started
    Connections {
        target: meetingController
        function onMeetingStateChanged(state) {
            if (state === "connected") {
                quickMeetScreen.meetingStarted("", "")
            }
        }
    }
}
