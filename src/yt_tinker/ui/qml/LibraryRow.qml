import QtQuick

Item {
    id: row

    required property string key
    required property string title
    required property string thumbnail
    required property string artist
    required property bool audio
    required property string size
    required property string date
    required property string path
    required property bool missing

    height: 60

    Accessible.role: Accessible.ListItem
    Accessible.name: title

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 1
        anchors.bottomMargin: 1
        radius: 8
        color: hover.hovered ? Theme.fill : "transparent"
        opacity: Theme.dark ? 0.5 : 0.6

        Behavior on color { ColorAnimation { duration: Theme.dur(120) } }
    }

    HoverHandler { id: hover }

    TapHandler {
        onDoubleTapped: if (!row.missing) bridge.openPath(row.path)
    }

    Thumbnail {
        id: art
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        width: row.audio ? 42 : 75
        height: 42
        source: row.thumbnail
        pixelWidth: 200
        radius: 6
        fallbackIcon: row.audio ? "music" : "video"
        opacity: row.missing ? 0.4 : 1
    }

    Column {
        anchors.left: parent.left
        anchors.leftMargin: 97
        anchors.right: size.left
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        spacing: 1

        AppText {
            width: parent.width
            text: row.title
            color: row.missing ? Theme.textSecondary : Theme.text
            font.weight: Font.Medium
        }

        AppText {
            width: parent.width
            text: row.missing ? "File moved or deleted" : row.artist
            color: Theme.textSecondary
            font.pixelSize: Theme.smallSize
        }
    }

    AppText {
        id: size
        anchors.right: date.left
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        width: 72
        horizontalAlignment: Text.AlignRight
        text: row.size
        color: Theme.textSecondary
        font.pixelSize: Theme.smallSize
        font.features: { "tnum": 1 }
    }

    AppText {
        id: date
        anchors.right: actions.left
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        width: 84
        horizontalAlignment: Text.AlignRight
        text: row.date
        color: Theme.textSecondary
        font.pixelSize: Theme.smallSize
    }

    Row {
        id: actions
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2

        IconButton {
            enabled: !row.missing
            opacity: row.missing ? 0.3 : 1
            icon: "play"
            label: "Open"
            tint: Theme.accent
            onClicked: bridge.openPath(row.path)
        }

        IconButton {
            enabled: !row.missing
            opacity: row.missing ? 0.3 : 1
            icon: "folder-open"
            label: "Show in Folder"
            onClicked: bridge.revealPath(row.path)
        }

        IconButton {
            icon: "trash-2"
            label: "Remove from Library"
            onClicked: bridge.removeFromLibrary(row.key)
        }
    }
}
