import QtQuick

Window {
    id: root

    // Every page stays alive, so switching is instant and typed text survives.
    component PageHost: Item {
        required property int index
        readonly property bool shown: root.page === index

        width: parent.width
        height: parent.height
        opacity: shown ? 1 : 0
        visible: opacity > 0
        y: shown ? 0 : 8

        Behavior on opacity { NumberAnimation { duration: Theme.dur(160) } }
        Behavior on y { NumberAnimation { duration: Theme.dur(200); easing.type: Easing.OutCubic } }
    }

    property int page: 0
    readonly property var searchPage: search

    width: 1120
    height: 760
    minimumWidth: 860
    minimumHeight: 560
    visible: true
    title: "YT Tinker"
    color: Theme.window
    flags: Qt.Window | Qt.ExpandedClientAreaHint | Qt.NoTitleBarBackgroundHint

    Component.onCompleted: {
        Theme.reduceMotion = bridge.reduceMotion
        search.focusSearch()
    }

    Connections {
        target: bridge
        function onToast(message) { toast.show(message) }
        function onDuplicateFound(title, path, token) {
            toast.showing = false
            sheet.show(title, path, token)
        }
    }

    Shortcut { sequence: "Ctrl+1"; onActivated: root.page = 0 }
    Shortcut { sequence: "Ctrl+2"; onActivated: root.page = 1 }
    Shortcut { sequence: "Ctrl+3"; onActivated: root.page = 2 }
    Shortcut { sequence: "Ctrl+4"; onActivated: root.page = 3 }
    Shortcut {
        sequences: ["Ctrl+L", "Ctrl+K"]
        onActivated: {
            root.page = 0
            search.focusSearch()
        }
    }

    Rectangle {
        id: sidebar
        width: 216
        height: parent.height
        color: Theme.sidebar

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 8
            y: 44
            spacing: 2

            Repeater {
                model: [
                    { icon: "search", label: "Search" },
                    { icon: "download", label: "Downloads" },
                    { icon: "library", label: "Library" },
                    { icon: "settings", label: "Settings" }
                ]

                SidebarItem {
                    required property var modelData
                    required property int index

                    width: parent.width
                    icon: modelData.icon
                    label: modelData.label
                    current: root.page === index
                    badge: index === 1 ? bridge.activeCount : 0
                    onActivated: root.page = index
                }
            }
        }

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 16
            spacing: 6
            visible: bridge.activeCount > 0
            opacity: visible ? 1 : 0

            Behavior on opacity { NumberAnimation { duration: Theme.dur(200) } }

            AppText {
                width: parent.width
                text: bridge.speedText || "Getting ready…"
                color: Theme.textSecondary
                font.pixelSize: Theme.smallSize
                font.features: { "tnum": 1 }
            }

            ProgressLine {
                width: parent.width
                value: bridge.overallFraction
            }
        }
    }

    Item {
        anchors.left: sidebar.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom

        PageHost { index: 0; SearchPage { id: search; anchors.fill: parent } }
        PageHost { index: 1; DownloadsPage { anchors.fill: parent } }
        PageHost { index: 2; LibraryPage { anchors.fill: parent } }
        PageHost { index: 3; SettingsPage { anchors.fill: parent } }
    }

    // The window has no title bar, so this strip does its job.
    Item {
        anchors.left: parent.left
        anchors.right: parent.right
        height: 36

        DragHandler {
            target: null
            onActiveChanged: if (active) root.startSystemMove()
        }

        TapHandler {
            acceptedButtons: Qt.LeftButton
            gesturePolicy: TapHandler.DragThreshold
            onDoubleTapped: root.visibility === Window.Maximized ? root.showNormal() : root.showMaximized()
        }
    }

    // A window without a title bar loses its native resize borders.
    component ResizeHandle: Item {
        required property int edges
        property int shape: Qt.SizeHorCursor

        visible: root.visibility !== Window.Maximized

        HoverHandler { cursorShape: parent.shape }

        DragHandler {
            target: null
            onActiveChanged: if (active) root.startSystemResize(parent.edges)
        }
    }

    ResizeHandle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: 36
        width: 6
        edges: Qt.LeftEdge
    }

    ResizeHandle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: 36
        width: 6
        edges: Qt.RightEdge
    }

    ResizeHandle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 6
        edges: Qt.BottomEdge
        shape: Qt.SizeVerCursor
    }

    ResizeHandle {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        width: 12
        height: 12
        edges: Qt.LeftEdge | Qt.BottomEdge
        shape: Qt.SizeBDiagCursor
    }

    ResizeHandle {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: 12
        height: 12
        edges: Qt.RightEdge | Qt.BottomEdge
        shape: Qt.SizeFDiagCursor
    }

    Toast { id: toast }
    DuplicateSheet { id: sheet }
}
