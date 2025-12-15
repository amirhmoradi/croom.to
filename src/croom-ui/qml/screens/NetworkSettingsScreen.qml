import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

/**
 * NetworkSettingsScreen.qml - WiFi and Network Configuration
 *
 * Provides:
 * - WiFi network scanning and connection
 * - Current network status
 * - Ethernet configuration
 * - Proxy settings
 * - Static IP configuration
 */
Item {
    id: networkSettingsScreen
    objectName: "networkSettingsScreen"

    signal backRequested()

    // Properties from controller
    property var currentNetwork: networkController.currentNetwork
    property var availableNetworks: networkController.availableNetworks
    property bool isScanning: networkController.isScanning
    property bool isConnected: networkController.isConnected
    property string connectionType: networkController.connectionType  // "wifi", "ethernet", "none"

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
            onClicked: networkSettingsScreen.backRequested()
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
            text: isScanning ? "\u23f3" : "\ud83d\udd04"
            font.pixelSize: 24
        }

        MouseArea {
            anchors.fill: parent
            enabled: !isScanning
            onClicked: networkController.scanNetworks()
        }

        RotationAnimation on rotation {
            from: 0
            to: 360
            duration: 2000
            loops: Animation.Infinite
            running: isScanning
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
            text: "Network Settings"
            color: "#ffffff"
            font.pixelSize: 28
            font.bold: true
        }

        // Current connection status card
        PiCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 120
            title: "Current Connection"

            RowLayout {
                anchors.fill: parent
                spacing: 16

                // Connection icon
                Rectangle {
                    Layout.preferredWidth: 60
                    Layout.preferredHeight: 60
                    radius: 30
                    color: isConnected ? "#4caf50" : "#f44336"

                    Text {
                        anchors.centerIn: parent
                        text: connectionType === "wifi" ? "\ud83d\udcf6" :
                              connectionType === "ethernet" ? "\ud83d\udd0c" : "\u274c"
                        font.pixelSize: 28
                    }
                }

                // Connection info
                Column {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: isConnected ?
                              (connectionType === "wifi" ? currentNetwork.ssid : "Ethernet") :
                              "Not connected"
                        color: "#ffffff"
                        font.pixelSize: 18
                        font.bold: true
                    }

                    Text {
                        text: isConnected ? networkController.ipAddress : "No network connection"
                        color: "#a0a0a0"
                        font.pixelSize: 14
                    }

                    Row {
                        spacing: 16
                        visible: isConnected

                        Text {
                            text: "Signal: " + (currentNetwork.signalStrength || 0) + "%"
                            color: "#a0a0a0"
                            font.pixelSize: 12
                            visible: connectionType === "wifi"
                        }

                        Text {
                            text: "Speed: " + networkController.linkSpeed
                            color: "#a0a0a0"
                            font.pixelSize: 12
                        }
                    }
                }

                // Disconnect button
                Rectangle {
                    Layout.preferredWidth: 100
                    Layout.preferredHeight: 40
                    radius: 20
                    color: "#f44336"
                    visible: isConnected

                    Text {
                        anchors.centerIn: parent
                        text: "Disconnect"
                        color: "#ffffff"
                        font.pixelSize: 14
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: networkController.disconnect()
                    }
                }
            }
        }

        // WiFi networks list
        PiCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Available WiFi Networks"

            ColumnLayout {
                anchors.fill: parent
                spacing: 8

                // Loading indicator
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 4
                    color: "#0f3460"
                    visible: isScanning

                    Rectangle {
                        id: scanProgress
                        width: parent.width * 0.3
                        height: parent.height
                        color: "#e94560"
                        radius: 2

                        SequentialAnimation on x {
                            loops: Animation.Infinite
                            running: isScanning
                            NumberAnimation {
                                from: 0
                                to: scanProgress.parent.width - scanProgress.width
                                duration: 1000
                            }
                            NumberAnimation {
                                from: scanProgress.parent.width - scanProgress.width
                                to: 0
                                duration: 1000
                            }
                        }
                    }
                }

                // Network list
                ListView {
                    id: networkList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 8

                    model: availableNetworks

                    delegate: Rectangle {
                        width: networkList.width
                        height: 60
                        radius: 8
                        color: mouseArea.containsMouse ? "#0f3460" : "transparent"

                        MouseArea {
                            id: mouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: showConnectDialog(modelData)
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 12

                            // Signal strength icon
                            Item {
                                Layout.preferredWidth: 32
                                Layout.preferredHeight: 32

                                Row {
                                    anchors.bottom: parent.bottom
                                    spacing: 2

                                    Repeater {
                                        model: 4

                                        Rectangle {
                                            width: 5
                                            height: 8 + (index * 6)
                                            radius: 1
                                            anchors.bottom: parent.bottom
                                            color: {
                                                var threshold = (index + 1) * 25
                                                return modelData.signalStrength >= threshold ?
                                                    (modelData.signalStrength >= 75 ? "#4caf50" :
                                                     modelData.signalStrength >= 50 ? "#ff9800" : "#f44336") :
                                                    "#333"
                                            }
                                        }
                                    }
                                }
                            }

                            // Network info
                            Column {
                                Layout.fillWidth: true
                                spacing: 2

                                Row {
                                    spacing: 8

                                    Text {
                                        text: modelData.ssid
                                        color: "#ffffff"
                                        font.pixelSize: 16
                                    }

                                    // Security icon
                                    Text {
                                        text: modelData.secured ? "\ud83d\udd12" : ""
                                        font.pixelSize: 12
                                        visible: modelData.secured
                                    }

                                    // Connected indicator
                                    Rectangle {
                                        visible: currentNetwork && currentNetwork.ssid === modelData.ssid
                                        width: connectedText.width + 12
                                        height: 18
                                        radius: 9
                                        color: "#4caf50"

                                        Text {
                                            id: connectedText
                                            anchors.centerIn: parent
                                            text: "Connected"
                                            color: "#ffffff"
                                            font.pixelSize: 10
                                        }
                                    }
                                }

                                Text {
                                    text: modelData.frequency + " GHz | " +
                                          modelData.security + " | " +
                                          modelData.signalStrength + "%"
                                    color: "#666"
                                    font.pixelSize: 12
                                }
                            }

                            // Connect/forget button
                            Rectangle {
                                Layout.preferredWidth: 80
                                Layout.preferredHeight: 32
                                radius: 16
                                color: currentNetwork && currentNetwork.ssid === modelData.ssid ?
                                       "#666" : "#e94560"
                                visible: mouseArea.containsMouse ||
                                         (currentNetwork && currentNetwork.ssid === modelData.ssid)

                                Text {
                                    anchors.centerIn: parent
                                    text: currentNetwork && currentNetwork.ssid === modelData.ssid ?
                                          "Forget" : "Connect"
                                    color: "#ffffff"
                                    font.pixelSize: 12
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        if (currentNetwork && currentNetwork.ssid === modelData.ssid) {
                                            networkController.forgetNetwork(modelData.ssid)
                                        } else {
                                            showConnectDialog(modelData)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Empty state
                    Text {
                        anchors.centerIn: parent
                        visible: networkList.count === 0 && !isScanning
                        text: "No WiFi networks found.\nTap refresh to scan again."
                        color: "#666"
                        font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                    }

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                    }
                }
            }
        }

        // Advanced settings button
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 50
            color: "#16213e"
            radius: 8

            RowLayout {
                anchors.fill: parent
                anchors.margins: 16

                Text {
                    text: "Advanced Network Settings"
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
                onClicked: advancedSettingsPopup.open()
            }
        }
    }

    // WiFi password dialog
    Popup {
        id: connectDialog
        modal: true
        anchors.centerIn: parent
        width: 450
        height: passwordRequired ? 380 : 280
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        property var network: null
        property bool passwordRequired: network ? network.secured : false
        property bool isConnecting: false

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
                text: "Connect to " + (connectDialog.network ? connectDialog.network.ssid : "")
                color: "#ffffff"
                font.pixelSize: 22
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
            }

            // Network info
            Row {
                Layout.alignment: Qt.AlignHCenter
                spacing: 16

                Text {
                    text: connectDialog.network ? (connectDialog.network.secured ? "\ud83d\udd12 Secured" : "\ud83d\udd13 Open") : ""
                    color: "#a0a0a0"
                    font.pixelSize: 14
                }

                Text {
                    text: connectDialog.network ? connectDialog.network.frequency + " GHz" : ""
                    color: "#a0a0a0"
                    font.pixelSize: 14
                }
            }

            // Password input
            Column {
                Layout.fillWidth: true
                spacing: 8
                visible: connectDialog.passwordRequired

                Text {
                    text: "Password"
                    color: "#a0a0a0"
                    font.pixelSize: 14
                }

                TextField {
                    id: passwordInput
                    width: parent.width
                    height: 50
                    placeholderText: "Enter WiFi password"
                    placeholderTextColor: "#666"
                    color: "#ffffff"
                    echoMode: showPasswordCheck.checked ? TextInput.Normal : TextInput.Password
                    font.pixelSize: 16

                    background: Rectangle {
                        color: "#16213e"
                        radius: 8
                        border.color: passwordInput.focus ? "#e94560" : "#333"
                        border.width: 2
                    }
                }

                CheckBox {
                    id: showPasswordCheck
                    text: "Show password"

                    contentItem: Text {
                        text: showPasswordCheck.text
                        color: "#a0a0a0"
                        font.pixelSize: 14
                        leftPadding: showPasswordCheck.indicator.width + 8
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            // Status message
            Text {
                Layout.fillWidth: true
                visible: connectDialog.isConnecting
                text: "Connecting..."
                color: "#e94560"
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
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
                        enabled: !connectDialog.isConnecting
                        onClicked: connectDialog.close()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 50
                    radius: 12
                    color: (!connectDialog.passwordRequired || passwordInput.text.length >= 8) ?
                           "#e94560" : "#666"

                    Text {
                        anchors.centerIn: parent
                        text: connectDialog.isConnecting ? "Connecting..." : "Connect"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: !connectDialog.isConnecting &&
                                 (!connectDialog.passwordRequired || passwordInput.text.length >= 8)
                        onClicked: {
                            connectDialog.isConnecting = true
                            networkController.connectToNetwork(
                                connectDialog.network.ssid,
                                passwordInput.text
                            )
                        }
                    }
                }
            }
        }

        onClosed: {
            passwordInput.text = ""
            isConnecting = false
        }
    }

    // Advanced settings popup
    Popup {
        id: advancedSettingsPopup
        modal: true
        anchors.centerIn: parent
        width: 500
        height: 500
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: "#1a1a2e"
            radius: 16
            border.color: "#333"
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: 16

            Text {
                Layout.fillWidth: true
                text: "Advanced Network Settings"
                color: "#ffffff"
                font.pixelSize: 22
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                ColumnLayout {
                    width: parent.width
                    spacing: 16

                    // IP Configuration
                    GroupBox {
                        Layout.fillWidth: true
                        title: "IP Configuration"

                        label: Text {
                            text: parent.title
                            color: "#a0a0a0"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        background: Rectangle {
                            color: "#16213e"
                            radius: 8
                            border.color: "#333"
                            border.width: 1
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 12

                            Row {
                                spacing: 16

                                RadioButton {
                                    id: dhcpRadio
                                    text: "DHCP (Automatic)"
                                    checked: true

                                    contentItem: Text {
                                        text: dhcpRadio.text
                                        color: "#ffffff"
                                        font.pixelSize: 14
                                        leftPadding: dhcpRadio.indicator.width + 8
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }

                                RadioButton {
                                    id: staticRadio
                                    text: "Static IP"

                                    contentItem: Text {
                                        text: staticRadio.text
                                        color: "#ffffff"
                                        font.pixelSize: 14
                                        leftPadding: staticRadio.indicator.width + 8
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }

                            // Static IP fields
                            GridLayout {
                                columns: 2
                                columnSpacing: 12
                                rowSpacing: 8
                                visible: staticRadio.checked

                                Text { text: "IP Address:"; color: "#a0a0a0"; font.pixelSize: 14 }
                                TextField {
                                    Layout.fillWidth: true
                                    height: 36
                                    placeholderText: "192.168.1.100"
                                    color: "#ffffff"
                                    background: Rectangle { color: "#0f3460"; radius: 4 }
                                }

                                Text { text: "Subnet Mask:"; color: "#a0a0a0"; font.pixelSize: 14 }
                                TextField {
                                    Layout.fillWidth: true
                                    height: 36
                                    placeholderText: "255.255.255.0"
                                    color: "#ffffff"
                                    background: Rectangle { color: "#0f3460"; radius: 4 }
                                }

                                Text { text: "Gateway:"; color: "#a0a0a0"; font.pixelSize: 14 }
                                TextField {
                                    Layout.fillWidth: true
                                    height: 36
                                    placeholderText: "192.168.1.1"
                                    color: "#ffffff"
                                    background: Rectangle { color: "#0f3460"; radius: 4 }
                                }

                                Text { text: "DNS Server:"; color: "#a0a0a0"; font.pixelSize: 14 }
                                TextField {
                                    Layout.fillWidth: true
                                    height: 36
                                    placeholderText: "8.8.8.8"
                                    color: "#ffffff"
                                    background: Rectangle { color: "#0f3460"; radius: 4 }
                                }
                            }
                        }
                    }

                    // Proxy settings
                    GroupBox {
                        Layout.fillWidth: true
                        title: "Proxy Settings"

                        label: Text {
                            text: parent.title
                            color: "#a0a0a0"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        background: Rectangle {
                            color: "#16213e"
                            radius: 8
                            border.color: "#333"
                            border.width: 1
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 12

                            CheckBox {
                                id: useProxyCheck
                                text: "Use Proxy Server"

                                contentItem: Text {
                                    text: useProxyCheck.text
                                    color: "#ffffff"
                                    font.pixelSize: 14
                                    leftPadding: useProxyCheck.indicator.width + 8
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }

                            GridLayout {
                                columns: 2
                                columnSpacing: 12
                                rowSpacing: 8
                                visible: useProxyCheck.checked

                                Text { text: "Proxy Host:"; color: "#a0a0a0"; font.pixelSize: 14 }
                                TextField {
                                    Layout.fillWidth: true
                                    height: 36
                                    placeholderText: "proxy.example.com"
                                    color: "#ffffff"
                                    background: Rectangle { color: "#0f3460"; radius: 4 }
                                }

                                Text { text: "Port:"; color: "#a0a0a0"; font.pixelSize: 14 }
                                TextField {
                                    Layout.fillWidth: true
                                    height: 36
                                    placeholderText: "8080"
                                    color: "#ffffff"
                                    background: Rectangle { color: "#0f3460"; radius: 4 }
                                }
                            }
                        }
                    }
                }
            }

            // Action buttons
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
                        onClicked: advancedSettingsPopup.close()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 44
                    radius: 8
                    color: "#e94560"

                    Text {
                        anchors.centerIn: parent
                        text: "Save"
                        color: "#ffffff"
                        font.pixelSize: 14
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            // Save advanced settings
                            networkController.saveAdvancedSettings({
                                useDhcp: dhcpRadio.checked,
                                useProxy: useProxyCheck.checked
                                // Add other fields
                            })
                            advancedSettingsPopup.close()
                        }
                    }
                }
            }
        }
    }

    function showConnectDialog(network) {
        connectDialog.network = network
        connectDialog.open()
    }

    // Handle connection results
    Connections {
        target: networkController

        function onConnectionResult(success, message) {
            connectDialog.isConnecting = false
            if (success) {
                connectDialog.close()
            }
        }
    }

    Component.onCompleted: {
        // Start scanning when screen opens
        networkController.scanNetworks()
    }
}
