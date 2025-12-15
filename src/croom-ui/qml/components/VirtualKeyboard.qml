import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/**
 * On-screen virtual keyboard for touch input.
 */
Rectangle {
    id: root

    property bool shiftActive: false
    property bool capsLock: false
    property string currentMode: "letters"  // letters, numbers, symbols

    signal keyPressed(string key)
    signal backspacePressed()
    signal enterPressed()
    signal spacePressed()

    color: "#1a1a2e"
    radius: 12

    height: 280

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        // Row 1
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 4

            Repeater {
                model: currentMode === "letters" ?
                    (shiftActive || capsLock ? ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"] :
                                               ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"]) :
                    currentMode === "numbers" ?
                    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"] :
                    ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")"]

                KeyButton {
                    text: modelData
                    onClicked: {
                        root.keyPressed(modelData)
                        if (shiftActive && !capsLock) shiftActive = false
                    }
                }
            }
        }

        // Row 2
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 4

            Item { width: 20; height: 1 }

            Repeater {
                model: currentMode === "letters" ?
                    (shiftActive || capsLock ? ["A", "S", "D", "F", "G", "H", "J", "K", "L"] :
                                               ["a", "s", "d", "f", "g", "h", "j", "k", "l"]) :
                    currentMode === "numbers" ?
                    ["-", "/", ":", ";", "(", ")", "$", "&", "@"] :
                    ["-", "_", "+", "=", "[", "]", "{", "}", "|"]

                KeyButton {
                    text: modelData
                    onClicked: {
                        root.keyPressed(modelData)
                        if (shiftActive && !capsLock) shiftActive = false
                    }
                }
            }

            Item { width: 20; height: 1 }
        }

        // Row 3
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 4

            // Shift key
            KeyButton {
                width: 70
                text: capsLock ? "⇪" : "⇧"
                isActive: shiftActive || capsLock
                onClicked: {
                    if (shiftActive) {
                        capsLock = !capsLock
                    } else {
                        shiftActive = true
                    }
                }
                onDoubleClicked: {
                    capsLock = true
                    shiftActive = true
                }
            }

            Repeater {
                model: currentMode === "letters" ?
                    (shiftActive || capsLock ? ["Z", "X", "C", "V", "B", "N", "M"] :
                                               ["z", "x", "c", "v", "b", "n", "m"]) :
                    currentMode === "numbers" ?
                    [".", ",", "?", "!", "'", "\"", ";"] :
                    ["~", "`", "\\", "<", ">", "?", "/"]

                KeyButton {
                    text: modelData
                    onClicked: {
                        root.keyPressed(modelData)
                        if (shiftActive && !capsLock) shiftActive = false
                    }
                }
            }

            // Backspace key
            KeyButton {
                width: 70
                text: "⌫"
                onClicked: root.backspacePressed()
            }
        }

        // Row 4 - Bottom row
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 4

            // Mode switch key
            KeyButton {
                width: 60
                text: currentMode === "letters" ? "123" : "ABC"
                onClicked: {
                    if (currentMode === "letters") {
                        currentMode = "numbers"
                    } else {
                        currentMode = "letters"
                    }
                }
            }

            // Symbols key
            KeyButton {
                width: 50
                text: currentMode === "symbols" ? "123" : "#+='"
                onClicked: {
                    if (currentMode === "symbols") {
                        currentMode = "numbers"
                    } else {
                        currentMode = "symbols"
                    }
                }
            }

            // Comma
            KeyButton {
                text: ","
                onClicked: root.keyPressed(",")
            }

            // Space bar
            KeyButton {
                width: 250
                text: "space"
                onClicked: root.spacePressed()
            }

            // Period
            KeyButton {
                text: "."
                onClicked: root.keyPressed(".")
            }

            // Enter key
            KeyButton {
                width: 80
                text: "↵"
                isAccent: true
                onClicked: root.enterPressed()
            }
        }
    }

    // Key button component
    component KeyButton: Rectangle {
        property string text: ""
        property bool isActive: false
        property bool isAccent: false

        signal clicked()
        signal doubleClicked()

        width: 44
        height: 48
        radius: 8
        color: {
            if (mouseArea.pressed) return Qt.darker(baseColor, 1.3)
            if (isActive) return "#e94560"
            return baseColor
        }

        readonly property color baseColor: isAccent ? "#e94560" : "#0f3460"

        Behavior on color {
            ColorAnimation { duration: 100 }
        }

        Text {
            anchors.centerIn: parent
            text: parent.text
            color: "#ffffff"
            font.pixelSize: text.length > 1 ? 12 : 20
            font.bold: true
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            onClicked: parent.clicked()
            onDoubleClicked: parent.doubleClicked()
        }
    }
}
