import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: joinMeetingScreen
    objectName: "joinMeetingScreen"

    property string prefillUrl: ""

    signal backRequested()
    signal meetingJoined()

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
            text: "←"
            color: "#ffffff"
            font.pixelSize: 24
        }

        MouseArea {
            anchors.fill: parent
            onClicked: joinMeetingScreen.backRequested()
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 32
        width: Math.min(600, parent.width - 48)

        // Title
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Join Meeting"
            color: "#ffffff"
            font.pixelSize: 36
            font.bold: true
        }

        // Meeting code input
        Column {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: "Enter meeting code or URL"
                color: "#a0a0a0"
                font.pixelSize: 16
            }

            TextField {
                id: meetingInput
                width: parent.width
                height: 60
                font.pixelSize: 20
                placeholderText: "e.g., abc-defg-hij or https://meet.google.com/..."
                placeholderTextColor: "#666"
                color: "#ffffff"
                text: prefillUrl

                background: Rectangle {
                    color: "#16213e"
                    radius: 12
                    border.color: meetingInput.focus ? "#e94560" : "#0f3460"
                    border.width: 2
                }
            }
        }

        // Platform buttons
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Or select platform:"
            color: "#a0a0a0"
            font.pixelSize: 16
        }

        Row {
            Layout.alignment: Qt.AlignHCenter
            spacing: 16

            // Google Meet
            Rectangle {
                width: 120
                height: 80
                color: meetingInput.text.indexOf("meet.google") >= 0 ? "#e94560" : "#16213e"
                radius: 12
                border.color: "#0f3460"
                border.width: 2

                Column {
                    anchors.centerIn: parent
                    spacing: 4

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "G"
                        color: "#4285f4"
                        font.pixelSize: 24
                        font.bold: true
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Meet"
                        color: "#ffffff"
                        font.pixelSize: 12
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: meetingInput.text = "https://meet.google.com/"
                }
            }

            // Teams
            Rectangle {
                width: 120
                height: 80
                color: meetingInput.text.indexOf("teams") >= 0 ? "#e94560" : "#16213e"
                radius: 12
                border.color: "#0f3460"
                border.width: 2

                Column {
                    anchors.centerIn: parent
                    spacing: 4

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "T"
                        color: "#6264a7"
                        font.pixelSize: 24
                        font.bold: true
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Teams"
                        color: "#ffffff"
                        font.pixelSize: 12
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: meetingInput.text = "https://teams.microsoft.com/l/meetup-join/"
                }
            }

            // Zoom
            Rectangle {
                width: 120
                height: 80
                color: meetingInput.text.indexOf("zoom") >= 0 ? "#e94560" : "#16213e"
                radius: 12
                border.color: "#0f3460"
                border.width: 2

                Column {
                    anchors.centerIn: parent
                    spacing: 4

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Z"
                        color: "#2d8cff"
                        font.pixelSize: 24
                        font.bold: true
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Zoom"
                        color: "#ffffff"
                        font.pixelSize: 12
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: meetingInput.text = "https://zoom.us/j/"
                }
            }
        }

        // Join button
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            width: 300
            height: 60
            color: meetingInput.text.length > 0 ? "#e94560" : "#666"
            radius: 12

            Text {
                anchors.centerIn: parent
                text: meetingController.meetingState === "joining" ? "Joining..." : "Join Meeting"
                color: "#ffffff"
                font.pixelSize: 20
                font.bold: true
            }

            MouseArea {
                anchors.fill: parent
                enabled: meetingInput.text.length > 0 && meetingController.meetingState !== "joining"
                onClicked: {
                    meetingController.joinMeeting(meetingInput.text)
                }
            }

            // Loading indicator
            Rectangle {
                anchors.right: parent.right
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                width: 24
                height: 24
                radius: 12
                color: "transparent"
                border.color: "#ffffff"
                border.width: 3
                visible: meetingController.meetingState === "joining"

                RotationAnimation on rotation {
                    from: 0
                    to: 360
                    duration: 1000
                    loops: Animation.Infinite
                    running: meetingController.meetingState === "joining"
                }
            }
        }

        // Camera/mic settings
        Row {
            Layout.alignment: Qt.AlignHCenter
            spacing: 32

            // Camera toggle
            Column {
                spacing: 8

                Rectangle {
                    width: 60
                    height: 60
                    radius: 30
                    color: meetingController.cameraOn ? "#4caf50" : "#666"

                    Text {
                        anchors.centerIn: parent
                        text: meetingController.cameraOn ? "📹" : "🚫"
                        font.pixelSize: 24
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
                    font.pixelSize: 12
                }
            }

            // Mic toggle
            Column {
                spacing: 8

                Rectangle {
                    width: 60
                    height: 60
                    radius: 30
                    color: !meetingController.muted ? "#4caf50" : "#666"

                    Text {
                        anchors.centerIn: parent
                        text: !meetingController.muted ? "🎤" : "🔇"
                        font.pixelSize: 24
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
                    font.pixelSize: 12
                }
            }
        }
    }

    // Handle successful join
    Connections {
        target: meetingController
        function onMeetingStateChanged(state) {
            if (state === "connected") {
                joinMeetingScreen.meetingJoined()
            }
        }
    }
}
