import QtQuick
import QtQuick.Controls.Basic as Controls

Controls.ScrollBar {
    id: bar
    padding: 3

    contentItem: Rectangle {
        implicitWidth: 6
        radius: 3
        color: Theme.textSecondary
        opacity: bar.active ? 0.5 : 0

        Behavior on opacity { NumberAnimation { duration: Theme.dur(200) } }
    }

    background: Item { }
}
