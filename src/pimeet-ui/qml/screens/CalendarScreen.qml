import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: calendarScreen
    objectName: "calendarScreen"

    signal backRequested()
    signal meetingSelected(string meetingUrl)

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
            onClicked: calendarScreen.backRequested()
        }
    }

    // Refresh button
    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 24
        width: 60
        height: 60
        color: "#16213e"
        radius: 30

        Text {
            anchors.centerIn: parent
            text: "🔄"
            font.pixelSize: 24
        }

        MouseArea {
            anchors.fill: parent
            onClicked: calendarController.refreshCalendar()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        anchors.topMargin: 100
        spacing: 16

        // Title
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Today's Meetings"
            color: "#ffffff"
            font.pixelSize: 28
            font.bold: true
        }

        // Date
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Qt.formatDate(new Date(), "dddd, MMMM d, yyyy")
            color: "#a0a0a0"
            font.pixelSize: 16
        }

        // Meeting list
        ListView {
            id: meetingsList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 12

            model: calendarController.meetings.length > 0 ? calendarController.meetings : demoMeetings

            // Demo meetings for development
            property var demoMeetings: [
                { title: "Team Standup", time: "9:00 AM - 9:30 AM", url: "https://meet.google.com/abc-defg-hij", platform: "google_meet" },
                { title: "Project Review", time: "11:00 AM - 12:00 PM", url: "https://teams.microsoft.com/l/meetup-join/...", platform: "teams" },
                { title: "Client Call", time: "2:00 PM - 3:00 PM", url: "https://zoom.us/j/123456789", platform: "zoom" },
                { title: "1:1 with Manager", time: "4:00 PM - 4:30 PM", url: "https://meet.google.com/xyz-abcd-efg", platform: "google_meet" }
            ]

            delegate: Rectangle {
                width: meetingsList.width
                height: 80
                color: "#16213e"
                radius: 12

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 16

                    // Platform icon
                    Rectangle {
                        Layout.preferredWidth: 48
                        Layout.preferredHeight: 48
                        radius: 24
                        color: {
                            if (modelData.platform === "google_meet") return "#4285f4"
                            if (modelData.platform === "teams") return "#6264a7"
                            if (modelData.platform === "zoom") return "#2d8cff"
                            return "#666"
                        }

                        Text {
                            anchors.centerIn: parent
                            text: {
                                if (modelData.platform === "google_meet") return "G"
                                if (modelData.platform === "teams") return "T"
                                if (modelData.platform === "zoom") return "Z"
                                return "?"
                            }
                            color: "#ffffff"
                            font.pixelSize: 24
                            font.bold: true
                        }
                    }

                    // Meeting info
                    Column {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            text: modelData.title
                            color: "#ffffff"
                            font.pixelSize: 18
                            font.bold: true
                        }

                        Text {
                            text: modelData.time
                            color: "#a0a0a0"
                            font.pixelSize: 14
                        }
                    }

                    // Join button
                    Rectangle {
                        Layout.preferredWidth: 80
                        Layout.preferredHeight: 40
                        color: "#e94560"
                        radius: 20

                        Text {
                            anchors.centerIn: parent
                            text: "Join"
                            color: "#ffffff"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: calendarScreen.meetingSelected(modelData.url)
                        }
                    }
                }
            }

            // Empty state
            Text {
                anchors.centerIn: parent
                visible: meetingsList.count === 0
                text: "No meetings scheduled for today"
                color: "#666"
                font.pixelSize: 18
            }
        }
    }
}
