import QtQuick

Item {
    id: card

    required property int index
    required property string title
    required property string thumbnail
    required property string duration
    required property string meta
    required property bool downloaded

    readonly property bool revealed: hover.hovered || videoButton.activeFocus || audioButton.activeFocus

    Accessible.role: Accessible.ListItem
    Accessible.name: title

    HoverHandler { id: hover }

    Thumbnail {
        id: art
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 8
        height: Math.round(width * 9 / 16)
        source: card.thumbnail
        radius: 10
        scale: hover.hovered ? 1.02 : 1

        Behavior on scale { NumberAnimation { duration: Theme.dur(220); easing.type: Easing.OutCubic } }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "#000000"
            opacity: card.revealed ? 0.45 : 0

            Behavior on opacity { NumberAnimation { duration: Theme.dur(140) } }
        }

        Rectangle {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 6
            visible: card.duration !== "" && !card.revealed
            width: time.implicitWidth + 10
            height: 20
            radius: 5
            color: "#B3000000"

            AppText {
                id: time
                anchors.centerIn: parent
                text: card.duration
                color: "#FFFFFF"
                font.pixelSize: Theme.smallSize
                font.features: { "tnum": 1 }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.margins: 6
            visible: card.downloaded && !card.revealed
            width: 22
            height: 20
            radius: 5
            color: Theme.positive

            Accessible.name: "Already downloaded"

            Icon {
                anchors.centerIn: parent
                name: "check"
                size: 13
                color: "#FFFFFF"
            }
        }

        Row {
            anchors.centerIn: parent
            spacing: 8
            opacity: card.revealed ? 1 : 0

            Behavior on opacity { NumberAnimation { duration: Theme.dur(140) } }

            PushButton {
                id: videoButton
                text: "Video"
                icon: "video"
                kind: "primary"
                onClicked: bridge.downloadResult(card.index, false)
            }

            PushButton {
                id: audioButton
                text: "Audio"
                icon: "music"
                onClicked: bridge.downloadResult(card.index, true)
            }
        }
    }

    AppText {
        id: name
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: art.bottom
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        anchors.topMargin: 8
        text: card.title
        wrapMode: Text.Wrap
        maximumLineCount: 2
        font.pixelSize: 13
        font.weight: Font.Medium
        lineHeight: 1.15
        verticalAlignment: Text.AlignTop
    }

    AppText {
        anchors.left: name.left
        anchors.right: name.right
        anchors.top: name.bottom
        anchors.topMargin: 3
        text: card.meta
        color: Theme.textSecondary
        font.pixelSize: Theme.smallSize
    }
}
