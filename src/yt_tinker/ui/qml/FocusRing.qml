import QtQuick

Rectangle {
    anchors.fill: parent
    anchors.margins: -3
    radius: (parent.radius ?? 8) + 3
    color: "transparent"
    border.color: Theme.accent
    border.width: 2
    visible: parent.activeFocus
}
