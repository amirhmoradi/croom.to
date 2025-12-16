import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/**
 * Meeting quality indicator showing network/audio/video quality.
 */
Rectangle {
    id: root

    property int qualityScore: 100  // 0-100
    property string qualityLevel: "excellent"  // excellent, good, fair, poor, critical
    property bool showDetails: false
    property real audioQuality: 100
    property real videoQuality: 100
    property real networkQuality: 100

    readonly property color qualityColor: {
        if (qualityScore >= 90) return "#4caf50"  // Green
        if (qualityScore >= 70) return "#8bc34a"  // Light green
        if (qualityScore >= 50) return "#ff9800"  // Orange
        if (qualityScore >= 30) return "#ff5722"  // Deep orange
        return "#f44336"  // Red
    }

    width: showDetails ? 200 : 50
    height: showDetails ? detailsColumn.height + 24 : 36
    radius: 8
    color: "#16213e"
    border.color: qualityColor
    border.width: 2

    Behavior on width {
        NumberAnimation { duration: 200; easing.type: Easing.OutQuad }
    }

    Behavior on height {
        NumberAnimation { duration: 200; easing.type: Easing.OutQuad }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: showDetails = !showDetails
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
    }

    // Compact view
    Row {
        anchors.centerIn: parent
        spacing: 6
        visible: !showDetails

        // Quality bars
        Row {
            spacing: 2
            anchors.verticalCenter: parent.verticalCenter

            Repeater {
                model: 4

                Rectangle {
                    width: 4
                    height: 6 + (index * 4)
                    radius: 2
                    color: {
                        var threshold = (index + 1) * 25
                        return qualityScore >= threshold ? qualityColor : "#333333"
                    }
                    anchors.bottom: parent.bottom
                }
            }
        }

        Text {
            text: qualityScore + "%"
            color: qualityColor
            font.pixelSize: 12
            font.bold: true
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    // Detailed view
    Column {
        id: detailsColumn
        anchors.centerIn: parent
        spacing: 8
        visible: showDetails
        width: parent.width - 24

        // Header
        Row {
            width: parent.width
            spacing: 8

            Text {
                text: "📶"
                font.pixelSize: 16
            }

            Text {
                text: "Connection Quality"
                color: "#ffffff"
                font.pixelSize: 14
                font.bold: true
            }

            Item { width: 1; height: 1; Layout.fillWidth: true }

            Text {
                text: qualityScore + "%"
                color: qualityColor
                font.pixelSize: 14
                font.bold: true
            }
        }

        // Quality bars
        Column {
            width: parent.width
            spacing: 6

            QualityBar {
                label: "🎤 Audio"
                value: audioQuality
                width: parent.width
            }

            QualityBar {
                label: "📹 Video"
                value: videoQuality
                width: parent.width
            }

            QualityBar {
                label: "🌐 Network"
                value: networkQuality
                width: parent.width
            }
        }

        // Status text
        Text {
            text: {
                if (qualityScore >= 90) return "✓ Excellent connection"
                if (qualityScore >= 70) return "✓ Good connection"
                if (qualityScore >= 50) return "⚠ Fair connection"
                if (qualityScore >= 30) return "⚠ Poor connection"
                return "✗ Connection issues"
            }
            color: qualityColor
            font.pixelSize: 12
        }
    }

    // Quality bar component
    component QualityBar: Row {
        property string label: ""
        property real value: 100

        spacing: 8

        Text {
            text: label
            color: "#a0a0a0"
            font.pixelSize: 12
            width: 80
        }

        Rectangle {
            width: parent.width - 80 - parent.spacing
            height: 8
            radius: 4
            color: "#333333"
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                width: parent.width * (value / 100)
                height: parent.height
                radius: parent.radius
                color: {
                    if (value >= 90) return "#4caf50"
                    if (value >= 70) return "#8bc34a"
                    if (value >= 50) return "#ff9800"
                    if (value >= 30) return "#ff5722"
                    return "#f44336"
                }

                Behavior on width {
                    NumberAnimation { duration: 300 }
                }
            }
        }
    }
}
