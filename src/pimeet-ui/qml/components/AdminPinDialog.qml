import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/**
 * AdminPinDialog.qml - PIN protection for admin/settings access
 *
 * Features:
 * - Numeric PIN entry
 * - Touch-friendly keypad
 * - Visual feedback
 * - Lockout after failed attempts
 * - Optional PIN change mode
 */
Popup {
    id: pinDialog
    modal: true
    closePolicy: Popup.NoAutoClose

    width: 360
    height: 480

    anchors.centerIn: parent

    // Properties
    property string title: "Enter Admin PIN"
    property int pinLength: 4
    property int maxAttempts: 5
    property int lockoutSeconds: 300
    property bool changePinMode: false
    property string newPinPrompt: "Enter New PIN"
    property string confirmPinPrompt: "Confirm New PIN"

    // Internal state
    property string enteredPin: ""
    property string newPin: ""
    property int failedAttempts: 0
    property int remainingLockout: 0
    property int step: 0  // 0: enter current, 1: enter new, 2: confirm new

    // Signals
    signal pinEntered(string pin)
    signal pinChanged(string oldPin, string newPin)
    signal cancelled()

    background: Rectangle {
        color: "#1a1a2e"
        radius: 16
        border.color: "#333"
        border.width: 1
    }

    contentItem: ColumnLayout {
        spacing: 20

        // Title
        Text {
            Layout.fillWidth: true
            text: changePinMode ? (step === 0 ? title : (step === 1 ? newPinPrompt : confirmPinPrompt)) : title
            color: "white"
            font.pixelSize: 22
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
        }

        // PIN display
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 12

            Repeater {
                model: pinLength

                Rectangle {
                    width: 48
                    height: 48
                    radius: 24
                    color: index < enteredPin.length ? "#6366f1" : "#333"
                    border.color: index === enteredPin.length ? "#6366f1" : "transparent"
                    border.width: 2

                    Rectangle {
                        anchors.centerIn: parent
                        width: 16
                        height: 16
                        radius: 8
                        color: "white"
                        visible: index < enteredPin.length
                    }

                    Behavior on color {
                        ColorAnimation { duration: 150 }
                    }
                }
            }
        }

        // Error/status message
        Text {
            Layout.fillWidth: true
            visible: failedAttempts > 0 || remainingLockout > 0
            text: remainingLockout > 0 ?
                  "Locked out. Try again in " + Math.ceil(remainingLockout / 60) + " min" :
                  "Incorrect PIN. " + (maxAttempts - failedAttempts) + " attempts remaining"
            color: "#ff4444"
            font.pixelSize: 14
            horizontalAlignment: Text.AlignHCenter
        }

        // Numeric keypad
        GridLayout {
            Layout.alignment: Qt.AlignHCenter
            columns: 3
            rowSpacing: 12
            columnSpacing: 12

            Repeater {
                model: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "back"]

                Rectangle {
                    width: 72
                    height: 72
                    radius: 36
                    color: modelData === "" ? "transparent" :
                           keyMouseArea.pressed ? "#4f46e5" : "#333"
                    visible: modelData !== ""

                    Text {
                        anchors.centerIn: parent
                        text: modelData === "back" ? "" : modelData
                        color: "white"
                        font.pixelSize: 28
                        font.bold: true
                    }

                    // Backspace icon
                    Image {
                        anchors.centerIn: parent
                        source: "qrc:/icons/backspace.svg"
                        width: 32
                        height: 32
                        visible: modelData === "back"
                    }

                    MouseArea {
                        id: keyMouseArea
                        anchors.fill: parent
                        enabled: remainingLockout <= 0
                        onClicked: handleKeyPress(modelData)
                    }

                    Behavior on color {
                        ColorAnimation { duration: 100 }
                    }
                }
            }
        }

        // Cancel button
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Item { Layout.fillWidth: true }

            Rectangle {
                width: 120
                height: 44
                radius: 22
                color: cancelMouseArea.pressed ? "#444" : "transparent"
                border.color: "#666"
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "Cancel"
                    color: "#aaa"
                    font.pixelSize: 16
                }

                MouseArea {
                    id: cancelMouseArea
                    anchors.fill: parent
                    onClicked: {
                        resetState()
                        cancelled()
                        pinDialog.close()
                    }
                }
            }

            Item { Layout.fillWidth: true }
        }
    }

    function handleKeyPress(key) {
        if (key === "back") {
            if (enteredPin.length > 0) {
                enteredPin = enteredPin.slice(0, -1)
            }
        } else if (enteredPin.length < pinLength) {
            enteredPin += key

            if (enteredPin.length === pinLength) {
                // PIN complete
                Qt.callLater(processPin)
            }
        }
    }

    function processPin() {
        if (changePinMode) {
            if (step === 0) {
                // Verify current PIN
                pinEntered(enteredPin)
                // Backend will call confirmCurrentPin() if correct
            } else if (step === 1) {
                // Store new PIN
                newPin = enteredPin
                enteredPin = ""
                step = 2
            } else {
                // Confirm new PIN
                if (enteredPin === newPin) {
                    pinChanged("", newPin)
                    resetState()
                    pinDialog.close()
                } else {
                    // PINs don't match
                    shakePinDisplay()
                    enteredPin = ""
                    step = 1
                    newPin = ""
                }
            }
        } else {
            // Normal PIN entry
            pinEntered(enteredPin)
        }
    }

    function confirmCurrentPin() {
        // Called by backend when current PIN is verified
        if (changePinMode && step === 0) {
            enteredPin = ""
            step = 1
        }
    }

    function pinAccepted() {
        resetState()
        pinDialog.close()
    }

    function pinRejected() {
        failedAttempts++

        if (failedAttempts >= maxAttempts) {
            remainingLockout = lockoutSeconds
            lockoutTimer.start()
        }

        shakePinDisplay()
        enteredPin = ""
    }

    function shakePinDisplay() {
        shakeAnimation.start()
    }

    function resetState() {
        enteredPin = ""
        newPin = ""
        step = 0
        failedAttempts = 0
        remainingLockout = 0
    }

    // Shake animation for wrong PIN
    SequentialAnimation {
        id: shakeAnimation
        target: contentItem

        NumberAnimation { property: "x"; to: -10; duration: 50 }
        NumberAnimation { property: "x"; to: 10; duration: 50 }
        NumberAnimation { property: "x"; to: -10; duration: 50 }
        NumberAnimation { property: "x"; to: 10; duration: 50 }
        NumberAnimation { property: "x"; to: 0; duration: 50 }
    }

    // Lockout timer
    Timer {
        id: lockoutTimer
        interval: 1000
        repeat: true
        onTriggered: {
            remainingLockout--
            if (remainingLockout <= 0) {
                remainingLockout = 0
                failedAttempts = 0
                stop()
            }
        }
    }

    // Reset on open
    onOpened: resetState()
}
