import QtQuick
import QtQuick.Effects
import QtQuick.Controls.Basic as Controls

Item {
    id: page

    readonly property bool idle: field.text.trim() === ""
    readonly property int gutter: 32

    function focusSearch() {
        field.focusInput()
    }

    // Links act instantly; typing waits for a pause so each key isn't a network call.
    function textEdited() {
        if (/^\s*(https?:\/\/|(www\.|m\.|music\.)?(youtube\.com|youtu\.be)\/)/i.test(field.text)) {
            debounce.stop()
            bridge.query(field.text)
        } else {
            debounce.restart()
        }
    }

    Timer {
        id: debounce
        interval: 380
        onTriggered: bridge.query(field.text)
    }

    Column {
        id: welcome
        anchors.horizontalCenter: parent.horizontalCenter
        y: field.y - height - 28
        spacing: 8
        opacity: page.idle ? 1 : 0
        visible: opacity > 0

        Behavior on opacity { NumberAnimation { duration: Theme.dur(180) } }

        PageTitle {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "What do you want to keep?"
            font.pixelSize: 34
        }

        AppText {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Paste a YouTube link, or search for any video or song."
            color: Theme.textSecondary
            font.pixelSize: 15
        }
    }

    SearchField {
        id: field
        objectName: "searchField"
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width - page.gutter * 2, 640)
        y: page.idle ? Math.round(parent.height * 0.42) : 52
        placeholder: "Paste a link or search YouTube"
        busy: bridge.searching
        onTextChanged: page.textEdited()
        onSubmitted: {
            debounce.stop()
            bridge.query(field.text)
        }

        Behavior on y { SpringAnimation { spring: 3.4; damping: 0.48; epsilon: 0.25; duration: Theme.dur(320) } }
    }

    Row {
        anchors.left: field.left
        anchors.top: field.bottom
        anchors.topMargin: 14
        spacing: 8
        visible: bridge.searchError !== "" && !page.idle

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            name: "circle-alert"
            color: Theme.negative
            size: 16
        }

        AppText {
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(implicitWidth, field.width - 24)
            text: bridge.searchError
            color: Theme.textSecondary
        }
    }

    Rectangle {
        id: previewCard
        anchors.left: field.left
        anchors.right: field.right
        anchors.top: field.bottom
        anchors.topMargin: 20
        height: 148
        radius: 14
        color: Theme.card
        visible: bridge.hasPreview && !page.idle
        opacity: visible ? 1 : 0

        Behavior on opacity { NumberAnimation { duration: Theme.dur(200) } }

        Thumbnail {
            id: previewArt
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.margins: 12
            width: height * 16 / 9
            source: bridge.preview.thumbnail ?? ""
            pixelWidth: 480
            fallbackIcon: "list-music"
        }

        Column {
            anchors.left: previewArt.right
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 12
            anchors.leftMargin: 16
            spacing: 4

            AppText {
                width: parent.width
                text: bridge.preview.title ?? ""
                wrapMode: Text.Wrap
                maximumLineCount: 2
                font.pixelSize: 15
                font.weight: Font.DemiBold
                verticalAlignment: Text.AlignTop
            }

            AppText {
                width: parent.width
                text: bridge.preview.meta ?? ""
                color: Theme.textSecondary
                font.pixelSize: 13
            }
        }

        Row {
            anchors.left: previewArt.right
            anchors.leftMargin: 16
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 12
            spacing: 8

            PushButton {
                text: bridge.preview.isPlaylist ? "All as Video" : "Video"
                icon: "video"
                kind: "primary"
                onClicked: bridge.downloadPreview(false)
            }

            PushButton {
                text: bridge.preview.isPlaylist ? "All as Audio" : "Audio"
                icon: "music"
                onClicked: bridge.downloadPreview(true)
            }

            PushButton {
                visible: bridge.preview.hasVideo ?? false
                text: "Just This Video"
                kind: "plain"
                onClicked: bridge.downloadPreviewVideo(false)
            }
        }
    }

    GridView {
        id: grid

        readonly property int columns: Math.max(2, Math.floor(width / 256))

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: field.bottom
        anchors.topMargin: 16
        anchors.leftMargin: page.gutter - 8
        anchors.rightMargin: page.gutter - 8
        visible: !page.idle
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        cellWidth: width / columns
        cellHeight: Math.round((cellWidth - 16) * 9 / 16) + 86
        cacheBuffer: 600
        model: bridge.results
        bottomMargin: 24
        delegate: ResultCard {
            width: grid.cellWidth
            height: grid.cellHeight
        }

        Controls.ScrollBar.vertical: Scroller { }
    }

    Grid {
        anchors.fill: grid
        anchors.topMargin: 0
        columns: grid.columns
        visible: bridge.searching && !bridge.hasPreview && grid.count === 0
                 && !/^\s*(https?:|(www\.|m\.|music\.)?(youtube\.com|youtu\.be)\/)/i.test(field.text)
        clip: true

        Repeater {
            model: grid.columns * 2

            Item {
                width: grid.cellWidth
                height: grid.cellHeight

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 10

                    Rectangle {
                        width: parent.width
                        height: Math.round(width * 9 / 16)
                        radius: 10
                        color: Theme.fill
                    }

                    Rectangle { width: parent.width * 0.85; height: 11; radius: 5; color: Theme.fill }
                    Rectangle { width: parent.width * 0.5; height: 11; radius: 5; color: Theme.fill }
                }
            }
        }

        SequentialAnimation on opacity {
            running: bridge.searching
            loops: Animation.Infinite
            NumberAnimation { from: 1; to: 0.55; duration: 620; easing.type: Easing.InOutSine }
            NumberAnimation { from: 0.55; to: 1; duration: 620; easing.type: Easing.InOutSine }
        }
    }
}
