import QtQuick

Item {
    id: row

    required property string rowId
    required property string title
    required property string thumbnail
    required property string status
    required property string detail
    required property real fraction
    required property bool audio
    required property string path

    readonly property bool active: status === "preparing" || status === "downloading" || status === "processing"
    readonly property bool failed: status === "failed"
    readonly property bool done: status === "completed"

    height: 76

    Accessible.role: Accessible.ListItem
    Accessible.name: title + ", " + detail

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 2
        anchors.bottomMargin: 2
        radius: 10
        color: hover.hovered ? Theme.fill : "transparent"
        opacity: Theme.dark ? 0.5 : 0.6

        Behavior on color { ColorAnimation { duration: Theme.dur(120) } }
    }

    HoverHandler { id: hover }

    Thumbnail {
        id: art
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        width: 96
        height: 54
        source: row.thumbnail
        pixelWidth: 240
        radius: 7
        fallbackIcon: row.audio ? "music" : "video"
    }

    Column {
        anchors.left: art.right
        anchors.leftMargin: 14
        anchors.right: actions.left
        anchors.rightMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        spacing: 5

        AppText {
            width: parent.width
            text: row.title
            font.weight: Font.Medium
        }

        ProgressLine {
            width: parent.width
            value: row.fraction
            tint: row.failed ? Theme.negative : row.done ? Theme.positive
                : row.status === "paused" ? Theme.textSecondary : Theme.accent
            visible: !row.done && !row.failed && row.status !== "queued"
        }

        Row {
            spacing: 5

            Icon {
                anchors.verticalCenter: parent.verticalCenter
                visible: row.failed || row.done
                name: row.failed ? "circle-alert" : "check"
                color: row.failed ? Theme.negative : Theme.positive
                size: 14
            }

            AppText {
                width: Math.min(implicitWidth, actions.x - art.width - 60)
                text: row.detail
                color: Theme.textSecondary
                font.pixelSize: Theme.smallSize
                font.features: { "tnum": 1 }
            }
        }
    }

    Row {
        id: actions
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2

        IconButton {
            visible: row.active || row.status === "queued"
            icon: "pause"
            label: "Pause"
            onClicked: bridge.pause(row.rowId)
        }

        IconButton {
            visible: row.status === "paused"
            icon: "play"
            label: "Resume"
            tint: Theme.accent
            onClicked: bridge.resume(row.rowId)
        }

        IconButton {
            visible: row.failed
            icon: "rotate-cw"
            label: "Retry"
            tint: Theme.accent
            onClicked: bridge.retry(row.rowId)
        }

        IconButton {
            visible: row.done && row.path !== ""
            icon: "play"
            label: "Open"
            tint: Theme.accent
            onClicked: bridge.openPath(row.path)
        }

        IconButton {
            visible: row.done && row.path !== ""
            icon: "folder-open"
            label: "Show in Folder"
            onClicked: bridge.revealPath(row.path)
        }

        IconButton {
            visible: !row.done
            icon: "x"
            label: row.failed ? "Remove" : "Cancel"
            onClicked: bridge.cancel(row.rowId)
        }
    }
}
