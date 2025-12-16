import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

Item {
    id: settingsScreen
    objectName: "settingsScreen"

    signal backRequested()
    signal networkSettingsRequested()
    signal audioVideoSettingsRequested()
    signal diagnosticsRequested()

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
            onClicked: settingsScreen.backRequested()
        }
    }

    // Admin mode indicator
    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 24
        width: adminModeRow.width + 24
        height: 40
        radius: 20
        color: settingsController.isAdminMode ? "#4caf50" : "transparent"
        border.color: settingsController.isAdminMode ? "#4caf50" : "#666"
        border.width: 1
        visible: settingsController.isAdminMode

        Row {
            id: adminModeRow
            anchors.centerIn: parent
            spacing: 8

            Text {
                text: "\ud83d\udd13"
                font.pixelSize: 16
            }

            Text {
                text: "Admin Mode"
                color: "#ffffff"
                font.pixelSize: 14
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: settingsController.exitAdminMode()
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

                // Network Settings (clickable)
                SettingsSection {
                    title: "Network"

                    Rectangle {
                        Layout.fillWidth: true
                        height: 50
                        color: "#16213e"
                        radius: 8

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16

                            Column {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    text: "WiFi & Network"
                                    color: "#ffffff"
                                    font.pixelSize: 16
                                }

                                Text {
                                    text: networkController.isConnected ?
                                          "Connected to " + (networkController.currentNetwork ? networkController.currentNetwork.ssid : "Unknown") :
                                          "Not connected"
                                    color: networkController.isConnected ? "#4caf50" : "#a0a0a0"
                                    font.pixelSize: 12
                                }
                            }

                            Text {
                                text: "\u203a"
                                color: "#666"
                                font.pixelSize: 24
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: settingsScreen.networkSettingsRequested()
                        }
                    }
                }

                // Audio/Video Settings (clickable)
                SettingsSection {
                    title: "Audio & Video"

                    Rectangle {
                        Layout.fillWidth: true
                        height: 50
                        color: "#16213e"
                        radius: 8

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16

                            Column {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    text: "Camera & Audio Devices"
                                    color: "#ffffff"
                                    font.pixelSize: 16
                                }

                                Text {
                                    text: avController.cameras.length + " camera(s), " +
                                          avController.microphones.length + " mic(s)"
                                    color: "#a0a0a0"
                                    font.pixelSize: 12
                                }
                            }

                            Text {
                                text: "\u203a"
                                color: "#666"
                                font.pixelSize: 24
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: settingsScreen.audioVideoSettingsRequested()
                        }
                    }

                    SettingsToggle {
                        label: "Camera on by default"
                        checked: meetingController.cameraOn
                        onCheckedChanged: {
                            // Save preference
                        }
                    }

                    SettingsToggle {
                        label: "Microphone on by default"
                        checked: !meetingController.muted
                        onCheckedChanged: {
                            // Save preference
                        }
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
                        value: "croom-" + roomController.roomName.toLowerCase().replace(/ /g, "-")
                    }

                    SettingsItem {
                        label: "Dashboard Connection"
                        value: networkController.isConnected ? "Connected" : "Disconnected"
                        valueColor: networkController.isConnected ? "#4caf50" : "#f44336"
                    }

                    // Diagnostics link
                    Rectangle {
                        Layout.fillWidth: true
                        height: 50
                        color: "#16213e"
                        radius: 8

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16

                            Text {
                                text: "System Diagnostics"
                                color: "#ffffff"
                                font.pixelSize: 16
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: "\u203a"
                                color: "#666"
                                font.pixelSize: 24
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: settingsScreen.diagnosticsRequested()
                        }
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
                            text: settingsController.isAdminMode ? "Exit Admin Mode" : "Enter Admin PIN"
                            color: "#e94560"
                            font.pixelSize: 16
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                if (settingsController.isAdminMode) {
                                    settingsController.exitAdminMode()
                                } else {
                                    adminPinDialog.open()
                                }
                            }
                        }
                    }

                    // Admin-only options
                    Column {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: settingsController.isAdminMode

                        Rectangle {
                            width: parent.width
                            height: 50
                            color: "#16213e"
                            radius: 8

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 16
                                anchors.rightMargin: 16

                                Text {
                                    text: "Change Admin PIN"
                                    color: "#ffffff"
                                    font.pixelSize: 16
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: "\u203a"
                                    color: "#666"
                                    font.pixelSize: 24
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    adminPinDialog.changePinMode = true
                                    adminPinDialog.open()
                                }
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 50
                            color: "#16213e"
                            radius: 8

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 16
                                anchors.rightMargin: 16

                                Text {
                                    text: "Factory Reset"
                                    color: "#f44336"
                                    font.pixelSize: 16
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: "\u203a"
                                    color: "#666"
                                    font.pixelSize: 24
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: factoryResetDialog.open()
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 50
                            color: "#16213e"
                            radius: 8

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 16
                                anchors.rightMargin: 16

                                Text {
                                    text: "Restart Device"
                                    color: "#ff9800"
                                    font.pixelSize: 16
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: "\u203a"
                                    color: "#666"
                                    font.pixelSize: 24
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: restartDialog.open()
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

    // Admin PIN Dialog
    AdminPinDialog {
        id: adminPinDialog

        onPinEntered: function(pin) {
            if (settingsController.verifyPin(pin)) {
                pinAccepted()
            } else {
                pinRejected()
            }
        }

        onPinChanged: function(oldPin, newPin) {
            settingsController.changePin(oldPin, newPin)
        }
    }

    // Factory Reset Confirmation Dialog
    Popup {
        id: factoryResetDialog
        modal: true
        anchors.centerIn: parent
        width: 400
        height: 200
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: "#1a1a2e"
            radius: 16
            border.color: "#f44336"
            border.width: 2
        }

        contentItem: ColumnLayout {
            spacing: 20

            Text {
                Layout.fillWidth: true
                text: "Factory Reset"
                color: "#f44336"
                font.pixelSize: 22
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
            }

            Text {
                Layout.fillWidth: true
                text: "This will erase all settings and return the device to factory defaults. This cannot be undone."
                color: "#a0a0a0"
                font.pixelSize: 14
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    height: 44
                    radius: 8
                    color: "transparent"
                    border.color: "#666"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "Cancel"
                        color: "#a0a0a0"
                        font.pixelSize: 14
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: factoryResetDialog.close()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 44
                    radius: 8
                    color: "#f44336"

                    Text {
                        anchors.centerIn: parent
                        text: "Reset Device"
                        color: "#ffffff"
                        font.pixelSize: 14
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            // Perform factory reset
                            factoryResetDialog.close()
                        }
                    }
                }
            }
        }
    }

    // Restart Confirmation Dialog
    Popup {
        id: restartDialog
        modal: true
        anchors.centerIn: parent
        width: 350
        height: 180
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
                text: "Restart Device?"
                color: "#ffffff"
                font.pixelSize: 22
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
            }

            Text {
                Layout.fillWidth: true
                text: "The device will restart and any active meeting will be disconnected."
                color: "#a0a0a0"
                font.pixelSize: 14
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    height: 44
                    radius: 8
                    color: "transparent"
                    border.color: "#666"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "Cancel"
                        color: "#a0a0a0"
                        font.pixelSize: 14
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: restartDialog.close()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 44
                    radius: 8
                    color: "#ff9800"

                    Text {
                        anchors.centerIn: parent
                        text: "Restart"
                        color: "#ffffff"
                        font.pixelSize: 14
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            // Perform restart
                            restartDialog.close()
                        }
                    }
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
