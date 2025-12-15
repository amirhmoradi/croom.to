import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: inMeetingScreen
    objectName: "inMeetingScreen"

    signal meetingEnded()

    // Meeting status indicator
    Rectangle {
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 24
        width: statusRow.width + 32
        height: 40
        radius: 20
        color: "#4caf50"

        Row {
            id: statusRow
            anchors.centerIn: parent
            spacing: 8

            Rectangle {
                width: 12
                height: 12
                radius: 6
                color: "#ffffff"

                SequentialAnimation on opacity {
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 500 }
                    NumberAnimation { to: 1.0; duration: 500 }
                }
            }

            Text {
                text: "In Meeting"
                color: "#ffffff"
                font.pixelSize: 16
                font.bold: true
            }
        }
    }

    // Main control buttons
    Row {
        anchors.centerIn: parent
        spacing: 48

        // Mute button
        Column {
            spacing: 12

            Rectangle {
                width: 100
                height: 100
                radius: 50
                color: !meetingController.muted ? "#4caf50" : "#f44336"

                Text {
                    anchors.centerIn: parent
                    text: !meetingController.muted ? "🎤" : "🔇"
                    font.pixelSize: 48
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: meetingController.toggleMute()
                    onPressed: parent.scale = 0.9
                    onReleased: parent.scale = 1.0
                }

                Behavior on scale {
                    NumberAnimation { duration: 100 }
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: !meetingController.muted ? "Mute" : "Unmute"
                color: "#ffffff"
                font.pixelSize: 16
            }
        }

        // Camera button
        Column {
            spacing: 12

            Rectangle {
                width: 100
                height: 100
                radius: 50
                color: meetingController.cameraOn ? "#4caf50" : "#666"

                Text {
                    anchors.centerIn: parent
                    text: meetingController.cameraOn ? "📹" : "🚫"
                    font.pixelSize: 48
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: meetingController.toggleCamera()
                    onPressed: parent.scale = 0.9
                    onReleased: parent.scale = 1.0
                }

                Behavior on scale {
                    NumberAnimation { duration: 100 }
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: meetingController.cameraOn ? "Stop Video" : "Start Video"
                color: "#ffffff"
                font.pixelSize: 16
            }
        }

        // End call button
        Column {
            spacing: 12

            Rectangle {
                width: 100
                height: 100
                radius: 50
                color: "#e94560"

                Text {
                    anchors.centerIn: parent
                    text: "📞"
                    font.pixelSize: 48
                    rotation: 135
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        meetingController.leaveMeeting()
                        inMeetingScreen.meetingEnded()
                    }
                    onPressed: parent.scale = 0.9
                    onReleased: parent.scale = 1.0
                }

                Behavior on scale {
                    NumberAnimation { duration: 100 }
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "End Call"
                color: "#ffffff"
                font.pixelSize: 16
            }
        }
    }

    // Meeting duration timer
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 80
        width: 150
        height: 50
        radius: 25
        color: "#16213e"

        Text {
            id: durationText
            anchors.centerIn: parent
            color: "#ffffff"
            font.pixelSize: 24
            font.family: "monospace"
            text: "00:00"

            property int seconds: 0

            Timer {
                interval: 1000
                running: meetingController.meetingState === "connected"
                repeat: true
                onTriggered: {
                    durationText.seconds++
                    var mins = Math.floor(durationText.seconds / 60)
                    var secs = durationText.seconds % 60
                    durationText.text = String(mins).padStart(2, '0') + ":" + String(secs).padStart(2, '0')
                }
            }
        }
    }

    // Occupancy indicator (if AI enabled)
    Rectangle {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 24
        width: occupancyRow.width + 24
        height: 40
        radius: 20
        color: "#16213e"
        visible: roomController.aiEnabled

        Row {
            id: occupancyRow
            anchors.centerIn: parent
            spacing: 8

            Text {
                text: "👥"
                font.pixelSize: 20
            }

            Text {
                text: roomController.occupancy + " in room"
                color: "#ffffff"
                font.pixelSize: 14
            }
        }
    }
}
