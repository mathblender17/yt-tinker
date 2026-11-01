import QtQuick

Rectangle {
    id: line

    property real value: 0
    property color tint: Theme.accent

    implicitHeight: 4
    radius: height / 2
    color: Theme.fill

    Accessible.role: Accessible.ProgressBar

    Rectangle {
        height: parent.height
        radius: parent.radius
        color: line.tint
        width: Math.max(parent.height, parent.width * Math.min(1, line.value))
        visible: line.value > 0

        Behavior on width { NumberAnimation { duration: Theme.dur(320); easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: Theme.dur(200) } }
    }
}
