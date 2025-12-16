import QtQuick 2.15
import QtQuick.Controls 2.15

/**
 * Card component for displaying content in a styled container.
 */
Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    property bool elevated: false
    property bool clickable: false
    property bool hoverable: true

    default property alias content: contentArea.data

    signal clicked()

    color: "#16213e"
    radius: 12
    border.color: hoverable && mouseArea.containsMouse ? "#0f3460" : "transparent"
    border.width: 2

    // Elevation shadow
    layer.enabled: elevated
    layer.effect: ShaderEffect {
        fragmentShader: "
            varying highp vec2 qt_TexCoord0;
            uniform sampler2D source;
            uniform lowp float qt_Opacity;
            void main() {
                lowp vec4 p = texture2D(source, qt_TexCoord0);
                gl_FragColor = vec4(0.0, 0.0, 0.0, 0.3 * p.a) * qt_Opacity;
            }
        "
    }

    Behavior on scale {
        NumberAnimation { duration: 100; easing.type: Easing.OutQuad }
    }

    Behavior on border.color {
        ColorAnimation { duration: 150 }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: clickable
        hoverEnabled: hoverable
        onClicked: root.clicked()
        onPressed: if (clickable) root.scale = 0.98
        onReleased: root.scale = 1.0
        onCanceled: root.scale = 1.0
        cursorShape: clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    Column {
        id: headerColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 16
        spacing: 4
        visible: title !== "" || subtitle !== ""

        Text {
            visible: title !== ""
            text: title
            color: "#ffffff"
            font.pixelSize: 18
            font.bold: true
            width: parent.width
            elide: Text.ElideRight
        }

        Text {
            visible: subtitle !== ""
            text: subtitle
            color: "#a0a0a0"
            font.pixelSize: 14
            width: parent.width
            elide: Text.ElideRight
        }
    }

    Item {
        id: contentArea
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: headerColumn.visible ? headerColumn.bottom : parent.top
        anchors.bottom: parent.bottom
        anchors.margins: 16
        anchors.topMargin: headerColumn.visible ? 12 : 16
    }
}
