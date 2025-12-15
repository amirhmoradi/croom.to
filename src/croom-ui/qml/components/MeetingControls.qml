import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/**
 * Meeting control bar for in-meeting screen.
 * Provides mute, camera, screen share, hand raise, reactions, and end meeting controls.
 */
Rectangle {
    id: root

    property bool isMuted: false
    property bool isCameraOn: true
    property bool isScreenSharing: false
    property bool isHandRaised: false
    property bool isRecording: false
    property bool showAdvancedControls: true

    signal muteToggled()
    signal cameraToggled()
    signal screenShareToggled()
    signal handRaiseToggled()
    signal reactionRequested(string reaction)
    signal layoutRequested()
    signal chatRequested()
    signal participantsRequested()
    signal recordingToggled()
    signal endMeetingRequested()

    height: 80
    color: "#16213e"
    radius: 16

    RowLayout {
        anchors.centerIn: parent
        spacing: 12

        // Mute button
        ControlButton {
            icon: isMuted ? "🔇" : "🎤"
            label: isMuted ? "Unmute" : "Mute"
            isActive: !isMuted
            activeColor: "#4caf50"
            inactiveColor: "#f44336"
            onClicked: root.muteToggled()
        }

        // Camera button
        ControlButton {
            icon: isCameraOn ? "📹" : "📷"
            label: isCameraOn ? "Camera Off" : "Camera On"
            isActive: isCameraOn
            activeColor: "#4caf50"
            inactiveColor: "#666666"
            onClicked: root.cameraToggled()
        }

        // Separator
        Rectangle {
            width: 1
            height: 50
            color: "#333333"
            visible: showAdvancedControls
        }

        // Screen share button
        ControlButton {
            visible: showAdvancedControls
            icon: isScreenSharing ? "🖥️" : "📺"
            label: isScreenSharing ? "Stop Share" : "Share"
            isActive: isScreenSharing
            activeColor: "#2196f3"
            onClicked: root.screenShareToggled()
        }

        // Hand raise button
        ControlButton {
            visible: showAdvancedControls
            icon: isHandRaised ? "🙌" : "✋"
            label: isHandRaised ? "Lower" : "Raise"
            isActive: isHandRaised
            activeColor: "#ff9800"
            onClicked: root.handRaiseToggled()
        }

        // Reactions button
        ControlButton {
            visible: showAdvancedControls
            icon: "😀"
            label: "React"
            onClicked: reactionMenu.open()

            Menu {
                id: reactionMenu
                y: -height - 10

                background: Rectangle {
                    color: "#16213e"
                    radius: 12
                    border.color: "#0f3460"
                    border.width: 1
                }

                Row {
                    padding: 8
                    spacing: 8

                    Repeater {
                        model: ["👍", "👎", "👏", "❤️", "😂", "😮"]

                        Rectangle {
                            width: 48
                            height: 48
                            radius: 8
                            color: reactionMouseArea.containsMouse ? "#0f3460" : "transparent"

                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                font.pixelSize: 28
                            }

                            MouseArea {
                                id: reactionMouseArea
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    root.reactionRequested(modelData)
                                    reactionMenu.close()
                                }
                            }
                        }
                    }
                }
            }
        }

        // Separator
        Rectangle {
            width: 1
            height: 50
            color: "#333333"
            visible: showAdvancedControls
        }

        // Layout button
        ControlButton {
            visible: showAdvancedControls
            icon: "⊞"
            label: "Layout"
            onClicked: root.layoutRequested()
        }

        // Chat button
        ControlButton {
            visible: showAdvancedControls
            icon: "💬"
            label: "Chat"
            onClicked: root.chatRequested()
        }

        // Participants button
        ControlButton {
            visible: showAdvancedControls
            icon: "👥"
            label: "People"
            onClicked: root.participantsRequested()
        }

        // Recording button (if available)
        ControlButton {
            visible: showAdvancedControls && meetingController.canRecord
            icon: isRecording ? "⏹️" : "⏺️"
            label: isRecording ? "Stop Rec" : "Record"
            isActive: isRecording
            activeColor: "#f44336"
            onClicked: root.recordingToggled()
        }

        // Separator
        Rectangle {
            width: 1
            height: 50
            color: "#333333"
        }

        // End meeting button
        Rectangle {
            width: 120
            height: 50
            radius: 25
            color: endMeetingMouseArea.pressed ? Qt.darker("#f44336", 1.2) : "#f44336"

            MouseArea {
                id: endMeetingMouseArea
                anchors.fill: parent
                onClicked: root.endMeetingRequested()
            }

            Row {
                anchors.centerIn: parent
                spacing: 8

                Text {
                    text: "📞"
                    font.pixelSize: 20
                }

                Text {
                    text: "End"
                    color: "#ffffff"
                    font.pixelSize: 16
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }

    // Control button component
    component ControlButton: Rectangle {
        property string icon: ""
        property string label: ""
        property bool isActive: true
        property color activeColor: "#0f3460"
        property color inactiveColor: "#333333"

        signal clicked()

        width: 70
        height: 60
        radius: 12
        color: mouseArea.containsMouse ? Qt.lighter(isActive ? activeColor : inactiveColor, 1.2) : (isActive ? activeColor : inactiveColor)

        Behavior on color {
            ColorAnimation { duration: 150 }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: parent.clicked()
        }

        Column {
            anchors.centerIn: parent
            spacing: 4

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: icon
                font.pixelSize: 24
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: label
                color: "#ffffff"
                font.pixelSize: 11
            }
        }
    }
}
