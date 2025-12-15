import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/**
 * Custom button component for Croom touch UI.
 * Supports icons, loading state, and different styles.
 */
Rectangle {
    id: root

    property string text: ""
    property string icon: ""
    property color buttonColor: "#e94560"
    property color textColor: "#ffffff"
    property color pressedColor: Qt.darker(buttonColor, 1.2)
    property color disabledColor: "#666666"
    property bool loading: false
    property bool enabled: true
    property int buttonWidth: 200
    property int buttonHeight: 60
    property string style: "primary"  // primary, secondary, outline, text

    signal clicked()

    width: buttonWidth
    height: buttonHeight
    radius: 12
    color: {
        if (!enabled) return disabledColor
        if (mouseArea.pressed) return pressedColor
        if (style === "outline" || style === "text") return "transparent"
        return buttonColor
    }
    border.color: style === "outline" ? buttonColor : "transparent"
    border.width: style === "outline" ? 2 : 0

    Behavior on scale {
        NumberAnimation { duration: 100; easing.type: Easing.OutQuad }
    }

    Behavior on color {
        ColorAnimation { duration: 150 }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.enabled && !root.loading
        onClicked: root.clicked()
        onPressed: root.scale = 0.95
        onReleased: root.scale = 1.0
        onCanceled: root.scale = 1.0
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    RowLayout {
        anchors.centerIn: parent
        spacing: 8
        visible: !loading

        // Icon
        Text {
            visible: icon !== ""
            text: icon
            font.pixelSize: root.height * 0.4
            color: root.enabled ? root.textColor : "#888888"
        }

        // Text
        Text {
            visible: root.text !== ""
            text: root.text
            color: root.enabled ? root.textColor : "#888888"
            font.pixelSize: root.height * 0.3
            font.bold: true
        }
    }

    // Loading spinner
    Item {
        anchors.centerIn: parent
        visible: loading
        width: height
        height: root.height * 0.5

        Rectangle {
            id: spinner
            width: parent.width
            height: width
            radius: width / 2
            color: "transparent"
            border.color: textColor
            border.width: 3
            opacity: 0.3
        }

        Rectangle {
            width: parent.width
            height: width
            radius: width / 2
            color: "transparent"
            border.color: textColor
            border.width: 3
            clip: true

            // Spinning arc
            Rectangle {
                width: parent.width
                height: parent.height
                color: textColor
                radius: width / 2
                x: -width / 2
            }

            RotationAnimator {
                target: parent
                from: 0
                to: 360
                duration: 1000
                running: loading
                loops: Animation.Infinite
            }
        }
    }
}
