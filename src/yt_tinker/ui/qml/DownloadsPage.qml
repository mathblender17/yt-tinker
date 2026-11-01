import QtQuick
import QtQuick.Controls.Basic as Controls

Item {
    id: page

    PageTitle {
        id: heading
        anchors.left: parent.left
        anchors.leftMargin: 32
        y: 44
        text: "Downloads"
    }

    AppText {
        anchors.left: heading.right
        anchors.leftMargin: 12
        anchors.baseline: heading.baseline
        visible: bridge.speedText !== ""
        text: bridge.speedText
        color: Theme.textSecondary
        font.features: { "tnum": 1 }
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: 32
        anchors.verticalCenter: heading.verticalCenter
        spacing: 8

        PushButton {
            visible: bridge.canResume
            text: "Resume All"
            onClicked: bridge.resumeAll()
        }

        PushButton {
            visible: bridge.canPause
            text: "Pause All"
            onClicked: bridge.pauseAll()
        }

        PushButton {
            visible: bridge.canClear
            text: "Clear Finished"
            onClicked: bridge.clearFinished()
        }
    }

    ListView {
        id: list
        anchors.fill: parent
        anchors.topMargin: 92
        anchors.leftMargin: 24
        anchors.rightMargin: 24
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: bridge.downloads
        bottomMargin: 24
        reuseItems: true
        section.property: "collection"
        section.delegate: AppText {
            required property string section
            width: list.width
            height: section === "" ? 0 : 34
            leftPadding: 8
            visible: section !== ""
            text: section
            color: Theme.textSecondary
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }
        delegate: DownloadRow { width: list.width }

        add: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.dur(200) }
            NumberAnimation { property: "scale"; from: 0.98; to: 1; duration: Theme.dur(200); easing.type: Easing.OutCubic }
        }
        remove: Transition {
            NumberAnimation { property: "opacity"; to: 0; duration: Theme.dur(140) }
        }
        displaced: Transition {
            NumberAnimation { properties: "y"; duration: Theme.dur(220); easing.type: Easing.OutCubic }
        }

        Controls.ScrollBar.vertical: Scroller { }
    }

    EmptyState {
        visible: list.count === 0
        icon: "arrow-down-to-line"
        title: "No downloads yet"
        message: "Anything you add from Search shows up here."
    }
}
