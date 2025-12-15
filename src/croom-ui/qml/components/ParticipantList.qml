import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/**
 * Participant list panel for meetings.
 */
Rectangle {
    id: root

    property var participants: []  // List of participant objects
    property bool isHost: false
    property string searchText: ""

    signal participantMuted(string participantId)
    signal participantRemoved(string participantId)
    signal participantSpotlighted(string participantId)

    color: "#16213e"
    radius: 12

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // Header
        Row {
            width: parent.width
            spacing: 8

            Text {
                text: "👥"
                font.pixelSize: 20
            }

            Text {
                text: "Participants (" + participants.length + ")"
                color: "#ffffff"
                font.pixelSize: 18
                font.bold: true
            }
        }

        // Search field
        Rectangle {
            width: parent.width
            height: 40
            radius: 8
            color: "#0f3460"

            Row {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                Text {
                    text: "🔍"
                    font.pixelSize: 16
                    anchors.verticalCenter: parent.verticalCenter
                }

                TextInput {
                    id: searchInput
                    width: parent.width - 30
                    height: parent.height
                    color: "#ffffff"
                    font.pixelSize: 14
                    verticalAlignment: TextInput.AlignVCenter
                    selectByMouse: true
                    onTextChanged: root.searchText = text

                    Text {
                        text: "Search participants..."
                        color: "#666666"
                        font.pixelSize: 14
                        visible: !searchInput.text && !searchInput.activeFocus
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }

        // Participant list
        ListView {
            id: participantListView
            width: parent.width
            height: parent.height - 100
            clip: true
            spacing: 8

            model: filteredParticipants

            delegate: ParticipantItem {
                width: participantListView.width
                participantName: modelData.name
                participantEmail: modelData.email || ""
                isHostParticipant: modelData.isHost
                isPresenter: modelData.isPresenter
                isMuted: modelData.isMuted
                isCameraOn: modelData.isCameraOn
                isHandRaised: modelData.isHandRaised
                showHostControls: root.isHost && !modelData.isHost

                onMuteClicked: root.participantMuted(modelData.id)
                onRemoveClicked: root.participantRemoved(modelData.id)
                onSpotlightClicked: root.participantSpotlighted(modelData.id)
            }

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }
        }
    }

    // Filter participants by search text
    property var filteredParticipants: {
        if (searchText === "") return participants
        var search = searchText.toLowerCase()
        return participants.filter(function(p) {
            return p.name.toLowerCase().indexOf(search) !== -1 ||
                   (p.email && p.email.toLowerCase().indexOf(search) !== -1)
        })
    }

    // Participant item component
    component ParticipantItem: Rectangle {
        property string participantName: ""
        property string participantEmail: ""
        property bool isHostParticipant: false
        property bool isPresenter: false
        property bool isMuted: false
        property bool isCameraOn: true
        property bool isHandRaised: false
        property bool showHostControls: false

        signal muteClicked()
        signal removeClicked()
        signal spotlightClicked()

        height: 56
        radius: 8
        color: mouseArea.containsMouse ? "#0f3460" : "transparent"

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
        }

        Row {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 12

            // Avatar
            Rectangle {
                width: 40
                height: 40
                radius: 20
                color: "#e94560"
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: participantName.charAt(0).toUpperCase()
                    color: "#ffffff"
                    font.pixelSize: 18
                    font.bold: true
                }
            }

            // Name and status
            Column {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 120
                spacing: 2

                Row {
                    spacing: 6

                    Text {
                        text: participantName
                        color: "#ffffff"
                        font.pixelSize: 14
                        elide: Text.ElideRight
                        width: Math.min(implicitWidth, 150)
                    }

                    // Host badge
                    Rectangle {
                        visible: isHostParticipant
                        width: hostBadgeText.width + 8
                        height: 16
                        radius: 4
                        color: "#e94560"
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            id: hostBadgeText
                            anchors.centerIn: parent
                            text: "Host"
                            color: "#ffffff"
                            font.pixelSize: 10
                        }
                    }

                    // Presenter badge
                    Rectangle {
                        visible: isPresenter
                        width: presenterBadgeText.width + 8
                        height: 16
                        radius: 4
                        color: "#2196f3"
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            id: presenterBadgeText
                            anchors.centerIn: parent
                            text: "Presenting"
                            color: "#ffffff"
                            font.pixelSize: 10
                        }
                    }
                }

                // Status icons
                Row {
                    spacing: 8

                    Text {
                        text: isMuted ? "🔇" : "🎤"
                        font.pixelSize: 12
                        opacity: isMuted ? 0.5 : 1
                    }

                    Text {
                        text: isCameraOn ? "📹" : "📷"
                        font.pixelSize: 12
                        opacity: isCameraOn ? 1 : 0.5
                    }

                    Text {
                        visible: isHandRaised
                        text: "✋"
                        font.pixelSize: 12
                    }
                }
            }

            // Host controls
            Row {
                visible: showHostControls && mouseArea.containsMouse
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4

                Rectangle {
                    width: 32
                    height: 32
                    radius: 16
                    color: muteBtn.containsMouse ? "#f44336" : "#333333"

                    Text {
                        anchors.centerIn: parent
                        text: "🔇"
                        font.pixelSize: 14
                    }

                    MouseArea {
                        id: muteBtn
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: muteClicked()
                    }
                }

                Rectangle {
                    width: 32
                    height: 32
                    radius: 16
                    color: spotlightBtn.containsMouse ? "#2196f3" : "#333333"

                    Text {
                        anchors.centerIn: parent
                        text: "📌"
                        font.pixelSize: 14
                    }

                    MouseArea {
                        id: spotlightBtn
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: spotlightClicked()
                    }
                }

                Rectangle {
                    width: 32
                    height: 32
                    radius: 16
                    color: removeBtn.containsMouse ? "#f44336" : "#333333"

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.pixelSize: 14
                        color: "#ffffff"
                    }

                    MouseArea {
                        id: removeBtn
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: removeClicked()
                    }
                }
            }
        }
    }
}
