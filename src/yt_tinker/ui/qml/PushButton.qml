import QtQuick

Rectangle {
    id: button

    property string text
    property string icon
    property string kind: "secondary"  // primary, secondary or plain
    readonly property bool primary: kind === "primary"
    readonly property color foreground: !enabled ? Theme.textSecondary
        : primary ? "#FFFFFF" : kind === "plain" ? Theme.accent : Theme.text

    signal clicked()

    implicitWidth: row.implicitWidth + 28
    implicitHeight: 32
    radius: 8
    opacity: enabled ? 1 : 0.55
    scale: tap.pressed ? 0.97 : 1
    color: primary ? (hover.hovered && enabled ? Theme.accentHover : Theme.accent)
        : kind === "plain" ? (hover.hovered && enabled ? Theme.fill : "transparent")
        : (hover.hovered && enabled ? Theme.fillHover : Theme.fill)
    activeFocusOnTab: enabled

    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.onPressAction: clicked()
    Keys.onReturnPressed: clicked()
    Keys.onSpacePressed: clicked()

    Behavior on color { ColorAnimation { duration: Theme.dur(120) } }
    Behavior on scale { NumberAnimation { duration: Theme.dur(120); easing.type: Easing.OutCubic } }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6

        Icon {
            anchors.verticalCenter: parent.verticalCenter
            visible: button.icon !== ""
            name: button.icon
            size: 15
            color: button.foreground
        }

        AppText {
            anchors.verticalCenter: parent.verticalCenter
            text: button.text
            color: button.foreground
            font.pixelSize: 13
            font.weight: Font.Medium
        }
    }

    HoverHandler {
        id: hover
        cursorShape: button.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    TapHandler {
        id: tap
        onTapped: if (button.enabled) button.clicked()
    }

    FocusRing { }
}
