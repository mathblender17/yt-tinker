import QtQuick
import QtQuick.Dialogs

Item {
    id: page

    FolderDialog {
        id: folderDialog
        title: "Choose a download folder"
        currentFolder: "file:///" + bridge.destination.replace(/\\/g, "/")
        onAccepted: bridge.setDestination(selectedFolder)
    }

    PageTitle {
        id: heading
        anchors.left: parent.left
        anchors.leftMargin: 32
        y: 44
        text: "Settings"
    }

    Column {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 32
        anchors.top: heading.bottom
        anchors.topMargin: 20
        spacing: 24

        SettingsGroup {
            width: Math.min(parent.width, 640)
            title: "Downloads"

            Item {
                width: parent.width
                height: 64

                Column {
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    anchors.right: changeFolder.left
                    anchors.rightMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    AppText { text: "Save to" }

                    AppText {
                        width: parent.width
                        text: bridge.destination
                        color: Theme.textSecondary
                        font.pixelSize: Theme.smallSize
                        elide: Text.ElideMiddle
                    }
                }

                PushButton {
                    id: changeFolder
                    anchors.right: parent.right
                    anchors.rightMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Change…"
                    onClicked: folderDialog.open()
                }
            }

            Rectangle { x: 16; width: parent.width - 16; height: 1; color: Theme.separator }

            Item {
                width: parent.width
                height: 64

                Column {
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    anchors.right: quality.left
                    anchors.rightMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    AppText { text: "Video quality" }

                    AppText {
                        width: parent.width
                        text: bridge.quality === "standard"
                            ? "Plays on every device. Up to 1080p."
                            : "Up to 4K. Some players need extra codecs."
                        color: Theme.textSecondary
                        font.pixelSize: Theme.smallSize
                    }
                }

                Segmented {
                    id: quality
                    anchors.right: parent.right
                    anchors.rightMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    width: 200
                    options: [
                        { label: "1080p", value: "standard" },
                        { label: "Maximum", value: "maximum" }
                    ]
                    value: bridge.quality
                    onActivated: value => bridge.setQuality(value)
                }
            }
        }

        SettingsGroup {
            width: Math.min(parent.width, 640)
            title: "Tools"

            Repeater {
                model: bridge.dependencies

                Item {
                    required property var modelData
                    required property int index

                    width: parent.width
                    height: 56

                    Rectangle {
                        x: 16
                        width: parent.width - 16
                        height: 1
                        color: Theme.separator
                        visible: parent.index > 0
                    }

                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 16
                        anchors.right: status.left
                        anchors.rightMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2

                        AppText { text: modelData.name }

                        AppText {
                            width: parent.width
                            text: modelData.detail
                            color: Theme.textSecondary
                            font.pixelSize: Theme.smallSize
                            elide: Text.ElideMiddle
                        }
                    }

                    Icon {
                        id: status
                        anchors.right: parent.right
                        anchors.rightMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        name: modelData.available ? "check" : "circle-alert"
                        color: modelData.available ? Theme.positive : Theme.negative
                        Accessible.name: modelData.available ? "Available" : "Missing"
                    }
                }
            }
        }
    }
}
