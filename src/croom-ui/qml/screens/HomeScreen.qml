import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: homeScreen
    objectName: "homeScreen"

    signal joinMeetingRequested()
    signal settingsRequested()
    signal calendarRequested()

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 32

        // Room name and status
        Column {
            Layout.alignment: Qt.AlignHCenter
            spacing: 8

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: roomController.roomName
                color: "#ffffff"
                font.pixelSize: 48
                font.bold: true
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: meetingController.meetingState === "idle" ? "Available" : "In Meeting"
                color: meetingController.meetingState === "idle" ? "#4caf50" : "#ff9800"
                font.pixelSize: 24
            }
        }

        // Next meeting info (if available)
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 500
            Layout.preferredHeight: upcomingMeetingColumn.height + 32
            color: "#16213e"
            radius: 12
            visible: calendarController.upcomingMeeting !== null

            Column {
                id: upcomingMeetingColumn
                anchors.centerIn: parent
                spacing: 8

                Text {
                    text: "Next Meeting"
                    color: "#a0a0a0"
                    font.pixelSize: 14
                }

                Text {
                    text: calendarController.upcomingMeeting ? calendarController.upcomingMeeting.title : ""
                    color: "#ffffff"
                    font.pixelSize: 20
                    font.bold: true
                }

                Text {
                    text: calendarController.upcomingMeeting ? calendarController.upcomingMeeting.time : ""
                    color: "#a0a0a0"
                    font.pixelSize: 16
                }
            }
        }

        // Action buttons
        Row {
            Layout.alignment: Qt.AlignHCenter
            spacing: 24

            // Join Meeting button
            Rectangle {
                width: 200
                height: 120
                color: "#e94560"
                radius: 16

                MouseArea {
                    anchors.fill: parent
                    onClicked: homeScreen.joinMeetingRequested()
                    onPressed: parent.scale = 0.95
                    onReleased: parent.scale = 1.0
                }

                Behavior on scale {
                    NumberAnimation { duration: 100 }
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 8

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "📹"
                        font.pixelSize: 36
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Join Meeting"
                        color: "#ffffff"
                        font.pixelSize: 18
                        font.bold: true
                    }
                }
            }

            // Calendar button
            Rectangle {
                width: 200
                height: 120
                color: "#0f3460"
                radius: 16

                MouseArea {
                    anchors.fill: parent
                    onClicked: homeScreen.calendarRequested()
                    onPressed: parent.scale = 0.95
                    onReleased: parent.scale = 1.0
                }

                Behavior on scale {
                    NumberAnimation { duration: 100 }
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 8

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "📅"
                        font.pixelSize: 36
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Calendar"
                        color: "#ffffff"
                        font.pixelSize: 18
                        font.bold: true
                    }
                }
            }

            // Settings button
            Rectangle {
                width: 200
                height: 120
                color: "#16213e"
                radius: 16
                border.color: "#0f3460"
                border.width: 2

                MouseArea {
                    anchors.fill: parent
                    onClicked: homeScreen.settingsRequested()
                    onPressed: parent.scale = 0.95
                    onReleased: parent.scale = 1.0
                }

                Behavior on scale {
                    NumberAnimation { duration: 100 }
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 8

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "⚙️"
                        font.pixelSize: 36
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Settings"
                        color: "#ffffff"
                        font.pixelSize: 18
                        font.bold: true
                    }
                }
            }
        }
    }
}
