import QtQuick
import QtQuick.Controls.Basic as Controls

Rectangle {
    id: button

    property string icon
    property string label
    property color tint: Theme.textSecondary

    signal clicked()

    width: 32
    height: 32
    radius: 8
    color: hover.hovered ? Theme.fill : "transparent"
    scale: tap.pressed ? 0.92 : 1
    activeFocusOnTab: true

    Accessible.role: Accessible.Button
    Accessible.name: label
    Accessible.onPressAction: clicked()
    Keys.onReturnPressed: clicked()
    Keys.onSpacePressed: clicked()

    Behavior on color { ColorAnimation { duration: Theme.dur(120) } }
    Behavior on scale { NumberAnimation { duration: Theme.dur(100) } }

    Icon {
        anchors.centerIn: parent
        name: button.icon
        size: 17
        color: button.tint
    }

    HoverHandler {
        id: hover
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        id: tap
        onTapped: button.clicked()
    }

    Controls.ToolTip {
        id: tip
        visible: hover.hovered
        delay: 500
        padding: 0
        y: button.height + 6
        background: Rectangle { radius: 6; color: Theme.card; border.color: Theme.separator }
        contentItem: AppText {
            text: button.label
            font.pixelSize: Theme.smallSize
            leftPadding: 8
            rightPadding: 8
            topPadding: 4
            bottomPadding: 4
        }
    }

    FocusRing { }
}
