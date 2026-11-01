import QtQuick
import QtQuick.Controls.Basic as Controls

Item {
    id: page

    property string kind: "all"

    function applyFilter() {
        bridge.setLibraryFilter(filter.text, kind)
    }

    PageTitle {
        id: heading
        anchors.left: parent.left
        anchors.leftMargin: 32
        y: 44
        text: "Library"
    }

    Segmented {
        anchors.right: parent.right
        anchors.rightMargin: 32
        anchors.verticalCenter: heading.verticalCenter
        width: 240
        options: [
            { label: "All", value: "all" },
            { label: "Video", value: "video" },
            { label: "Music", value: "audio" }
        ]
        value: page.kind
        onActivated: value => {
            page.kind = value
            page.applyFilter()
        }
    }

    SearchField {
        id: filter
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 32
        anchors.rightMargin: 32
        y: 92
        fieldHeight: 36
        placeholder: "Filter by title or artist"
        onTextChanged: page.applyFilter()
    }

    ListView {
        id: list
        anchors.fill: parent
        anchors.topMargin: 140
        anchors.leftMargin: 24
        anchors.rightMargin: 24
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: bridge.library
        bottomMargin: 24
        reuseItems: true
        delegate: LibraryRow { width: list.width }

        Controls.ScrollBar.vertical: Scroller { }
    }

    EmptyState {
        visible: list.count === 0
        icon: "library"
        title: filter.text || page.kind !== "all" ? "Nothing matches" : "Your library is empty"
        message: filter.text || page.kind !== "all" ? "Try a different filter." : "Finished downloads are collected here."
    }
}
