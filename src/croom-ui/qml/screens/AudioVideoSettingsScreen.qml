import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

/**
 * AudioVideoSettingsScreen.qml - Audio and Video Device Configuration
 *
 * Provides:
 * - Camera selection and preview
 * - Microphone selection with level meter
 * - Speaker selection with test
 * - Audio processing settings
 * - Video quality settings
 */
Item {
    id: avSettingsScreen
    objectName: "audioVideoSettingsScreen"

    signal backRequested()

    // Properties from controller
    property var cameras: avController.cameras
    property var microphones: avController.microphones
    property var speakers: avController.speakers
    property int selectedCameraIndex: avController.selectedCameraIndex
    property int selectedMicIndex: avController.selectedMicIndex
    property int selectedSpeakerIndex: avController.selectedSpeakerIndex
    property real micLevel: avController.micLevel  // 0.0 - 1.0
    property bool isTestingAudio: avController.isTestingAudio

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
            onClicked: avSettingsScreen.backRequested()
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
            text: "Audio & Video Settings"
            color: "#ffffff"
            font.pixelSize: 28
            font.bold: true
        }

        // Main content - 2 column layout
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 24

            // Left column - Video
            PiCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: parent.width / 2
                title: "Camera"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 16

                    // Camera preview
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 200
                        color: "#0d0d1a"
                        radius: 8

                        // Camera preview placeholder
                        Item {
                            id: cameraPreview
                            anchors.fill: parent

                            // Video output would be rendered here
                            Text {
                                anchors.centerIn: parent
                                text: cameras.length > 0 ? "\ud83d\udcf9" : "\ud83d\udeab"
                                font.pixelSize: 48
                                visible: !avController.previewActive
                            }

                            Text {
                                anchors.bottom: parent.bottom
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.bottomMargin: 8
                                text: cameras.length > 0 ?
                                      (avController.previewActive ? "Preview active" : "Click to preview") :
                                      "No camera detected"
                                color: "#666"
                                font.pixelSize: 12
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            enabled: cameras.length > 0
                            onClicked: avController.togglePreview()
                        }
                    }

                    // Camera selection
                    ComboBox {
                        id: cameraCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 50
                        model: cameras
                        currentIndex: selectedCameraIndex
                        displayText: cameras.length > 0 ?
                                    cameras[currentIndex].name : "No cameras available"

                        delegate: ItemDelegate {
                            width: cameraCombo.width
                            height: 44

                            contentItem: Text {
                                text: modelData.name
                                color: "#ffffff"
                                font.pixelSize: 14
                                verticalAlignment: Text.AlignVCenter
                            }

                            background: Rectangle {
                                color: highlighted ? "#0f3460" : "transparent"
                            }
                        }

                        background: Rectangle {
                            color: "#16213e"
                            radius: 8
                            border.color: cameraCombo.pressed ? "#e94560" : "#333"
                            border.width: 1
                        }

                        contentItem: Text {
                            text: cameraCombo.displayText
                            color: "#ffffff"
                            font.pixelSize: 14
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 12
                        }

                        popup: Popup {
                            y: cameraCombo.height
                            width: cameraCombo.width
                            padding: 0

                            background: Rectangle {
                                color: "#1a1a2e"
                                radius: 8
                                border.color: "#333"
                            }

                            contentItem: ListView {
                                implicitHeight: contentHeight
                                model: cameraCombo.popup.visible ? cameraCombo.delegateModel : null
                                clip: true
                            }
                        }

                        onCurrentIndexChanged: {
                            if (currentIndex !== selectedCameraIndex) {
                                avController.setCamera(currentIndex)
                            }
                        }
                    }

                    // Video quality settings
                    Column {
                        Layout.fillWidth: true
                        spacing: 12

                        Text {
                            text: "Video Quality"
                            color: "#a0a0a0"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        // Resolution
                        Row {
                            width: parent.width
                            spacing: 12

                            Text {
                                text: "Resolution:"
                                color: "#a0a0a0"
                                font.pixelSize: 14
                                width: 100
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            ComboBox {
                                id: resolutionCombo
                                width: parent.width - 112
                                height: 40
                                model: ["1080p (1920x1080)", "720p (1280x720)", "480p (854x480)", "360p (640x360)"]
                                currentIndex: avController.resolutionIndex

                                background: Rectangle {
                                    color: "#0f3460"
                                    radius: 4
                                }

                                contentItem: Text {
                                    text: resolutionCombo.currentText
                                    color: "#ffffff"
                                    font.pixelSize: 12
                                    leftPadding: 8
                                    verticalAlignment: Text.AlignVCenter
                                }

                                onCurrentIndexChanged: avController.setResolution(currentIndex)
                            }
                        }

                        // Frame rate
                        Row {
                            width: parent.width
                            spacing: 12

                            Text {
                                text: "Frame Rate:"
                                color: "#a0a0a0"
                                font.pixelSize: 14
                                width: 100
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            ComboBox {
                                id: fpsCombo
                                width: parent.width - 112
                                height: 40
                                model: ["30 fps", "25 fps", "15 fps"]
                                currentIndex: avController.fpsIndex

                                background: Rectangle {
                                    color: "#0f3460"
                                    radius: 4
                                }

                                contentItem: Text {
                                    text: fpsCombo.currentText
                                    color: "#ffffff"
                                    font.pixelSize: 12
                                    leftPadding: 8
                                    verticalAlignment: Text.AlignVCenter
                                }

                                onCurrentIndexChanged: avController.setFrameRate(currentIndex)
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // Right column - Audio
            PiCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: parent.width / 2
                title: "Audio"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 16

                    // Microphone section
                    Column {
                        Layout.fillWidth: true
                        spacing: 12

                        Text {
                            text: "Microphone"
                            color: "#a0a0a0"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        ComboBox {
                            id: micCombo
                            width: parent.width
                            height: 50
                            model: microphones
                            currentIndex: selectedMicIndex
                            displayText: microphones.length > 0 ?
                                        microphones[currentIndex].name : "No microphones available"

                            background: Rectangle {
                                color: "#16213e"
                                radius: 8
                                border.color: micCombo.pressed ? "#e94560" : "#333"
                                border.width: 1
                            }

                            contentItem: Text {
                                text: micCombo.displayText
                                color: "#ffffff"
                                font.pixelSize: 14
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 12
                            }

                            onCurrentIndexChanged: {
                                if (currentIndex !== selectedMicIndex) {
                                    avController.setMicrophone(currentIndex)
                                }
                            }
                        }

                        // Mic level meter
                        Column {
                            width: parent.width
                            spacing: 4

                            Text {
                                text: "Input Level"
                                color: "#666"
                                font.pixelSize: 12
                            }

                            Rectangle {
                                width: parent.width
                                height: 20
                                radius: 4
                                color: "#0d0d1a"

                                Rectangle {
                                    width: parent.width * micLevel
                                    height: parent.height
                                    radius: parent.radius
                                    color: micLevel > 0.8 ? "#f44336" :
                                           micLevel > 0.6 ? "#ff9800" : "#4caf50"

                                    Behavior on width {
                                        NumberAnimation { duration: 50 }
                                    }
                                }

                                // Peak indicator marks
                                Row {
                                    anchors.fill: parent
                                    anchors.leftMargin: parent.width * 0.6

                                    Rectangle {
                                        width: 1
                                        height: parent.height
                                        color: "#ff9800"
                                        opacity: 0.5
                                    }

                                    Item { width: (parent.width - parent.anchors.leftMargin) * 0.33 - 1; height: 1 }

                                    Rectangle {
                                        width: 1
                                        height: parent.height
                                        color: "#f44336"
                                        opacity: 0.5
                                    }
                                }
                            }
                        }

                        // Mic volume slider
                        Row {
                            width: parent.width
                            spacing: 12

                            Text {
                                text: "\ud83c\udfa4"
                                font.pixelSize: 20
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Slider {
                                id: micVolumeSlider
                                width: parent.width - 60
                                from: 0
                                to: 100
                                value: avController.micVolume

                                background: Rectangle {
                                    x: micVolumeSlider.leftPadding
                                    y: micVolumeSlider.topPadding + micVolumeSlider.availableHeight / 2 - height / 2
                                    width: micVolumeSlider.availableWidth
                                    height: 6
                                    radius: 3
                                    color: "#333"

                                    Rectangle {
                                        width: micVolumeSlider.visualPosition * parent.width
                                        height: parent.height
                                        color: "#4caf50"
                                        radius: 3
                                    }
                                }

                                handle: Rectangle {
                                    x: micVolumeSlider.leftPadding + micVolumeSlider.visualPosition * (micVolumeSlider.availableWidth - width)
                                    y: micVolumeSlider.topPadding + micVolumeSlider.availableHeight / 2 - height / 2
                                    width: 20
                                    height: 20
                                    radius: 10
                                    color: micVolumeSlider.pressed ? "#e94560" : "#ffffff"
                                }

                                onValueChanged: avController.setMicVolume(value)
                            }

                            Text {
                                text: Math.round(micVolumeSlider.value) + "%"
                                color: "#ffffff"
                                font.pixelSize: 12
                                width: 36
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: "#333"
                    }

                    // Speaker section
                    Column {
                        Layout.fillWidth: true
                        spacing: 12

                        Text {
                            text: "Speaker"
                            color: "#a0a0a0"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        ComboBox {
                            id: speakerCombo
                            width: parent.width
                            height: 50
                            model: speakers
                            currentIndex: selectedSpeakerIndex
                            displayText: speakers.length > 0 ?
                                        speakers[currentIndex].name : "No speakers available"

                            background: Rectangle {
                                color: "#16213e"
                                radius: 8
                                border.color: speakerCombo.pressed ? "#e94560" : "#333"
                                border.width: 1
                            }

                            contentItem: Text {
                                text: speakerCombo.displayText
                                color: "#ffffff"
                                font.pixelSize: 14
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 12
                            }

                            onCurrentIndexChanged: {
                                if (currentIndex !== selectedSpeakerIndex) {
                                    avController.setSpeaker(currentIndex)
                                }
                            }
                        }

                        // Speaker volume slider
                        Row {
                            width: parent.width
                            spacing: 12

                            Text {
                                text: "\ud83d\udd0a"
                                font.pixelSize: 20
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Slider {
                                id: speakerVolumeSlider
                                width: parent.width - 60
                                from: 0
                                to: 100
                                value: avController.speakerVolume

                                background: Rectangle {
                                    x: speakerVolumeSlider.leftPadding
                                    y: speakerVolumeSlider.topPadding + speakerVolumeSlider.availableHeight / 2 - height / 2
                                    width: speakerVolumeSlider.availableWidth
                                    height: 6
                                    radius: 3
                                    color: "#333"

                                    Rectangle {
                                        width: speakerVolumeSlider.visualPosition * parent.width
                                        height: parent.height
                                        color: "#2196f3"
                                        radius: 3
                                    }
                                }

                                handle: Rectangle {
                                    x: speakerVolumeSlider.leftPadding + speakerVolumeSlider.visualPosition * (speakerVolumeSlider.availableWidth - width)
                                    y: speakerVolumeSlider.topPadding + speakerVolumeSlider.availableHeight / 2 - height / 2
                                    width: 20
                                    height: 20
                                    radius: 10
                                    color: speakerVolumeSlider.pressed ? "#e94560" : "#ffffff"
                                }

                                onValueChanged: avController.setSpeakerVolume(value)
                            }

                            Text {
                                text: Math.round(speakerVolumeSlider.value) + "%"
                                color: "#ffffff"
                                font.pixelSize: 12
                                width: 36
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // Test speaker button
                        Rectangle {
                            width: parent.width
                            height: 44
                            radius: 8
                            color: isTestingAudio ? "#666" : "#0f3460"

                            Row {
                                anchors.centerIn: parent
                                spacing: 8

                                Text {
                                    text: isTestingAudio ? "\u23f9" : "\u25b6"
                                    font.pixelSize: 16
                                    color: "#ffffff"
                                }

                                Text {
                                    text: isTestingAudio ? "Playing test sound..." : "Test Speaker"
                                    color: "#ffffff"
                                    font.pixelSize: 14
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: avController.testSpeaker()
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: "#333"
                    }

                    // Audio processing
                    Column {
                        Layout.fillWidth: true
                        spacing: 12

                        Text {
                            text: "Audio Processing"
                            color: "#a0a0a0"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        // Echo cancellation
                        Row {
                            width: parent.width

                            Text {
                                text: "Echo Cancellation"
                                color: "#ffffff"
                                font.pixelSize: 14
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Item { width: parent.width - 200; height: 1 }

                            Switch {
                                id: echoCancelSwitch
                                checked: avController.echoCancellation
                                onCheckedChanged: avController.setEchoCancellation(checked)
                            }
                        }

                        // Noise suppression
                        Row {
                            width: parent.width

                            Text {
                                text: "Noise Suppression"
                                color: "#ffffff"
                                font.pixelSize: 14
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Item { width: parent.width - 200; height: 1 }

                            Switch {
                                id: noiseSuppressionSwitch
                                checked: avController.noiseSuppression
                                onCheckedChanged: avController.setNoiseSuppression(checked)
                            }
                        }

                        // Auto gain
                        Row {
                            width: parent.width

                            Text {
                                text: "Auto Gain Control"
                                color: "#ffffff"
                                font.pixelSize: 14
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Item { width: parent.width - 200; height: 1 }

                            Switch {
                                id: autoGainSwitch
                                checked: avController.autoGainControl
                                onCheckedChanged: avController.setAutoGainControl(checked)
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }

        // Bottom action bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: "#16213e"
            radius: 8

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12

                // Reset to defaults
                Rectangle {
                    Layout.preferredWidth: 150
                    Layout.preferredHeight: 40
                    radius: 8
                    color: "transparent"
                    border.color: "#666"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "Reset to Defaults"
                        color: "#a0a0a0"
                        font.pixelSize: 14
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: avController.resetToDefaults()
                    }
                }

                Item { Layout.fillWidth: true }

                // Device info
                Text {
                    text: cameras.length + " camera(s), " +
                          microphones.length + " mic(s), " +
                          speakers.length + " speaker(s) detected"
                    color: "#666"
                    font.pixelSize: 12
                }

                Item { Layout.fillWidth: true }

                // Refresh devices
                Rectangle {
                    Layout.preferredWidth: 150
                    Layout.preferredHeight: 40
                    radius: 8
                    color: "#0f3460"

                    Row {
                        anchors.centerIn: parent
                        spacing: 8

                        Text {
                            text: "\ud83d\udd04"
                            font.pixelSize: 16
                        }

                        Text {
                            text: "Refresh Devices"
                            color: "#ffffff"
                            font.pixelSize: 14
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: avController.refreshDevices()
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        // Refresh device list when screen opens
        avController.refreshDevices()
    }

    Component.onDestruction: {
        // Stop preview when leaving screen
        avController.stopPreview()
    }
}
