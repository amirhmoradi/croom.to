import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

/**
 * DiagnosticsScreen.qml - System health and diagnostics display
 *
 * Provides real-time system health monitoring:
 * - CPU, Memory, Temperature
 * - Network connectivity
 * - Service status
 * - Hardware status
 * - Log viewer
 * - Diagnostic tests
 */
Rectangle {
    id: diagnosticsScreen
    color: "#1a1a2e"

    // Properties from backend
    property var systemInfo: ({})
    property var serviceStatus: ({})
    property var networkStatus: ({})
    property var hardwareStatus: ({})
    property var recentLogs: []
    property bool isRunningDiagnostics: false

    // Signals
    signal runDiagnostics()
    signal exportLogs()
    signal restartService(string serviceName)
    signal backPressed()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // Header
        RowLayout {
            Layout.fillWidth: true

            PiButton {
                text: "Back"
                icon.source: "qrc:/icons/back.svg"
                onClicked: backPressed()
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "System Diagnostics"
                font.pixelSize: 24
                font.bold: true
                color: "white"
            }

            Item { Layout.fillWidth: true }

            PiButton {
                text: isRunningDiagnostics ? "Running..." : "Run Tests"
                enabled: !isRunningDiagnostics
                loading: isRunningDiagnostics
                onClicked: runDiagnostics()
            }
        }

        // Main content grid
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 2
            columnSpacing: 16
            rowSpacing: 16

            // System Resources Card
            PiCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 200
                title: "System Resources"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    // CPU
                    ResourceBar {
                        Layout.fillWidth: true
                        label: "CPU"
                        value: systemInfo.cpu_percent || 0
                        warningThreshold: 70
                        criticalThreshold: 90
                    }

                    // Memory
                    ResourceBar {
                        Layout.fillWidth: true
                        label: "Memory"
                        value: systemInfo.memory_percent || 0
                        warningThreshold: 80
                        criticalThreshold: 95
                    }

                    // Disk
                    ResourceBar {
                        Layout.fillWidth: true
                        label: "Disk"
                        value: systemInfo.disk_percent || 0
                        warningThreshold: 80
                        criticalThreshold: 95
                    }

                    // Temperature
                    RowLayout {
                        Layout.fillWidth: true

                        Text {
                            text: "Temperature:"
                            color: "#aaa"
                            font.pixelSize: 14
                        }

                        Text {
                            text: (systemInfo.temperature || 0).toFixed(1) + " C"
                            color: systemInfo.temperature > 80 ? "#ff4444" :
                                   systemInfo.temperature > 70 ? "#ffaa00" : "#44ff44"
                            font.pixelSize: 14
                            font.bold: true
                        }
                    }
                }
            }

            // Network Status Card
            PiCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 200
                title: "Network Status"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    StatusRow {
                        label: "Internet"
                        status: networkStatus.internet_connected ? "Connected" : "Disconnected"
                        isOk: networkStatus.internet_connected || false
                    }

                    StatusRow {
                        label: "Local IP"
                        status: networkStatus.local_ip || "N/A"
                        isOk: networkStatus.local_ip !== ""
                    }

                    StatusRow {
                        label: "WiFi Signal"
                        status: (networkStatus.wifi_signal || 0) + " dBm"
                        isOk: (networkStatus.wifi_signal || -100) > -70
                    }

                    StatusRow {
                        label: "DNS"
                        status: networkStatus.dns_working ? "OK" : "Failed"
                        isOk: networkStatus.dns_working || false
                    }

                    StatusRow {
                        label: "Dashboard"
                        status: networkStatus.dashboard_connected ? "Connected" : "Disconnected"
                        isOk: networkStatus.dashboard_connected || false
                    }
                }
            }

            // Services Status Card
            PiCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 200
                title: "Services"

                ListView {
                    anchors.fill: parent
                    anchors.margins: 12
                    clip: true
                    spacing: 6

                    model: Object.keys(serviceStatus)

                    delegate: RowLayout {
                        width: parent.width
                        height: 32

                        Rectangle {
                            width: 12
                            height: 12
                            radius: 6
                            color: serviceStatus[modelData].running ? "#44ff44" : "#ff4444"
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData
                            color: "white"
                            font.pixelSize: 14
                            elide: Text.ElideRight
                        }

                        Text {
                            text: serviceStatus[modelData].status || "unknown"
                            color: "#aaa"
                            font.pixelSize: 12
                        }

                        PiButton {
                            implicitWidth: 60
                            implicitHeight: 24
                            text: "Restart"
                            style: "outline"
                            visible: !serviceStatus[modelData].running
                            onClicked: restartService(modelData)
                        }
                    }
                }
            }

            // Hardware Status Card
            PiCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 200
                title: "Hardware"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    StatusRow {
                        label: "Camera"
                        status: hardwareStatus.camera ? "Detected" : "Not Found"
                        isOk: hardwareStatus.camera || false
                    }

                    StatusRow {
                        label: "Microphone"
                        status: hardwareStatus.microphone ? "Detected" : "Not Found"
                        isOk: hardwareStatus.microphone || false
                    }

                    StatusRow {
                        label: "Speaker"
                        status: hardwareStatus.speaker ? "Detected" : "Not Found"
                        isOk: hardwareStatus.speaker || false
                    }

                    StatusRow {
                        label: "Display"
                        status: hardwareStatus.display_resolution || "Unknown"
                        isOk: true
                    }

                    StatusRow {
                        label: "Touch"
                        status: hardwareStatus.touch_enabled ? "Enabled" : "Disabled"
                        isOk: hardwareStatus.touch_enabled || false
                    }
                }
            }

            // Log Viewer Card (spans both columns)
            PiCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 250
                Layout.columnSpan: 2
                title: "Recent Logs"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true

                        ComboBox {
                            id: logLevelFilter
                            model: ["All", "Error", "Warning", "Info", "Debug"]
                            currentIndex: 0
                        }

                        Item { Layout.fillWidth: true }

                        PiButton {
                            text: "Export Logs"
                            icon.source: "qrc:/icons/download.svg"
                            onClicked: exportLogs()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#0d0d1a"
                        radius: 8

                        ListView {
                            id: logListView
                            anchors.fill: parent
                            anchors.margins: 8
                            clip: true
                            spacing: 4

                            model: recentLogs.filter(function(log) {
                                if (logLevelFilter.currentIndex === 0) return true;
                                var levels = ["error", "warning", "info", "debug"];
                                return log.level === levels[logLevelFilter.currentIndex - 1];
                            })

                            delegate: Text {
                                width: parent.width
                                text: modelData.timestamp + " [" + modelData.level.toUpperCase() + "] " + modelData.message
                                color: modelData.level === "error" ? "#ff4444" :
                                       modelData.level === "warning" ? "#ffaa00" :
                                       modelData.level === "debug" ? "#888" : "#ccc"
                                font.family: "monospace"
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }

    // Resource bar component
    component ResourceBar: RowLayout {
        property string label: ""
        property real value: 0
        property real warningThreshold: 70
        property real criticalThreshold: 90

        spacing: 8

        Text {
            Layout.preferredWidth: 60
            text: label
            color: "#aaa"
            font.pixelSize: 14
        }

        Rectangle {
            Layout.fillWidth: true
            height: 16
            radius: 8
            color: "#333"

            Rectangle {
                width: parent.width * (value / 100)
                height: parent.height
                radius: 8
                color: value > criticalThreshold ? "#ff4444" :
                       value > warningThreshold ? "#ffaa00" : "#44ff44"

                Behavior on width {
                    NumberAnimation { duration: 300 }
                }
            }
        }

        Text {
            Layout.preferredWidth: 50
            text: value.toFixed(1) + "%"
            color: value > criticalThreshold ? "#ff4444" :
                   value > warningThreshold ? "#ffaa00" : "white"
            font.pixelSize: 14
            horizontalAlignment: Text.AlignRight
        }
    }

    // Status row component
    component StatusRow: RowLayout {
        property string label: ""
        property string status: ""
        property bool isOk: true

        spacing: 8

        Rectangle {
            width: 10
            height: 10
            radius: 5
            color: isOk ? "#44ff44" : "#ff4444"
        }

        Text {
            Layout.preferredWidth: 100
            text: label + ":"
            color: "#aaa"
            font.pixelSize: 14
        }

        Text {
            Layout.fillWidth: true
            text: status
            color: "white"
            font.pixelSize: 14
        }
    }

    // Refresh timer
    Timer {
        interval: 5000
        running: true
        repeat: true
        onTriggered: {
            // Backend would update systemInfo, networkStatus, etc.
        }
    }
}
