import QtQuick
import QtQuick.Effects

Item {
    id: sheet

    property string title
    property string path
    property string token
    property bool open: false

    function show(newTitle, newPath, newToken) {
        title = newTitle
        path = newPath
        token = newToken
        open = true
        openButton.forceActiveFocus()
    }

    anchors.fill: parent
    visible: opacity > 0
    opacity: open ? 1 : 0

    Behavior on opacity { NumberAnimation { duration: Theme.dur(160) } }

    Rectangle {
        anchors.fill: parent
        color: Theme.scrim

        TapHandler { onTapped: sheet.open = false }
    }

    RectangularShadow {
        anchors.fill: card
        radius: card.radius
        blur: 40
        offset.y: 12
        color: Theme.shadow
    }

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: 420
        height: content.implicitHeight + 48
        radius: 14
        color: Theme.card
        scale: sheet.open ? 1 : 0.96

        Accessible.role: Accessible.Dialog
        Accessible.name: "Already downloaded"
        Keys.onEscapePressed: sheet.open = false

        Behavior on scale { SpringAnimation { spring: 5; damping: 0.5; epsilon: 0.002; duration: Theme.dur(260) } }

        TapHandler { }

        Column {
            id: content
            anchors.fill: parent
            anchors.margins: 24
            spacing: 8

            AppText {
                width: parent.width
                text: "Already downloaded"
                font.pixelSize: 17
                font.weight: Font.DemiBold
            }

            AppText {
                width: parent.width
                text: sheet.title
                maximumLineCount: 2
                wrapMode: Text.Wrap
            }

            AppText {
                width: parent.width
                text: sheet.path
                color: Theme.textSecondary
                font.pixelSize: Theme.smallSize
                elide: Text.ElideMiddle
            }

            Item { width: 1; height: 12 }

            Row {
                anchors.right: parent.right
                spacing: 8

                PushButton {
                    text: "Cancel"
                    kind: "plain"
                    Keys.onEscapePressed: sheet.open = false
                    onClicked: sheet.open = false
                }

                PushButton {
                    text: "Download Again"
                    Keys.onEscapePressed: sheet.open = false
                    onClicked: {
                        sheet.open = false
                        bridge.downloadAgain(sheet.token)
                    }
                }

                PushButton {
                    id: openButton
                    text: "Open File"
                    kind: "primary"
                    Keys.onEscapePressed: sheet.open = false
                    onClicked: {
                        sheet.open = false
                        bridge.openPath(sheet.path)
                    }
                }
            }
        }
    }
}
