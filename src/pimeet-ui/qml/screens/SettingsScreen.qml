import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: settingsScreen
    objectName: "settingsScreen"

    signal backRequested()

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
            onClicked: settingsScreen.backRequested()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        anchors.topMargin: 100
        spacing: 24

        // Title
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Settings"
            color: "#ffffff"
            font.pixelSize: 28
            font.bold: true
        }

        // Settings list
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: 16

                // Room Settings
                SettingsSection {
                    title: "Room"

                    SettingsItem {
                        label: "Room Name"
                        value: roomController.roomName
                    }

                    SettingsItem {
                        label: "Room Location"
                        value: "Building A, Floor 2"
                    }
                }

                // Audio/Video Settings
                SettingsSection {
                    title: "Audio & Video"

                    SettingsToggle {
                        label: "Camera on by default"
                        checked: true
                    }

                    SettingsToggle {
                        label: "Microphone on by default"
                        checked: true
                    }

                    SettingsItem {
                        label: "Audio Input"
                        value: "USB Microphone"
                        showArrow: true
                    }

                    SettingsItem {
                        label: "Audio Output"
                        value: "HDMI Audio"
                        showArrow: true
                    }
                }

                // AI Settings
                SettingsSection {
                    title: "AI Features"
                    visible: roomController.aiEnabled

                    SettingsToggle {
                        label: "Auto-framing"
                        checked: true
                    }

                    SettingsToggle {
                        label: "Noise reduction"
                        checked: true
                    }

                    SettingsToggle {
                        label: "Occupancy counting"
                        checked: true
                    }
                }

                // System Info
                SettingsSection {
                    title: "System"

                    SettingsItem {
                        label: "Software Version"
                        value: "2.0.0-dev"
                    }

                    SettingsItem {
                        label: "Device ID"
                        value: "pi-room-001"
                    }

                    SettingsItem {
                        label: "Dashboard Connection"
                        value: "Connected"
                        valueColor: "#4caf50"
                    }
                }

                // Admin section
                SettingsSection {
                    title: "Administration"

                    Rectangle {
                        Layout.fillWidth: true
                        height: 50
                        color: "#16213e"
                        radius: 8

                        Text {
                            anchors.centerIn: parent
                            text: "Enter Admin PIN"
                            color: "#e94560"
                            font.pixelSize: 16
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                // TODO: Show PIN dialog
                            }
                        }
                    }
                }

                Item {
                    Layout.preferredHeight: 40
                }
            }
        }
    }

    // Settings Section component
    component SettingsSection: ColumnLayout {
        property string title: ""
        Layout.fillWidth: true
        spacing: 8

        Text {
            text: title
            color: "#a0a0a0"
            font.pixelSize: 14
            font.bold: true
            Layout.topMargin: 16
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#0f3460"
        }
    }

    // Settings Item component
    component SettingsItem: Rectangle {
        property string label: ""
        property string value: ""
        property color valueColor: "#a0a0a0"
        property bool showArrow: false

        Layout.fillWidth: true
        height: 50
        color: "#16213e"
        radius: 8

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16

            Text {
                text: label
                color: "#ffffff"
                font.pixelSize: 16
            }

            Item { Layout.fillWidth: true }

            Text {
                text: value
                color: valueColor
                font.pixelSize: 16
            }

            Text {
                visible: showArrow
                text: "›"
                color: "#666"
                font.pixelSize: 20
            }
        }
    }

    // Settings Toggle component
    component SettingsToggle: Rectangle {
        property string label: ""
        property bool checked: false

        Layout.fillWidth: true
        height: 50
        color: "#16213e"
        radius: 8

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16

            Text {
                text: label
                color: "#ffffff"
                font.pixelSize: 16
            }

            Item { Layout.fillWidth: true }

            Switch {
                checked: parent.parent.checked
                onCheckedChanged: parent.parent.checked = checked
            }
        }
    }
}
