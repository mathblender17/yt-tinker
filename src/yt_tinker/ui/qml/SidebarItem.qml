import QtQuick

Rectangle {
    id: item

    property string icon
    property string label
    property int badge: 0
    property bool current: false

    signal activated()

    height: 34
    radius: 8
    color: current ? (Theme.dark ? "#3A3A3C" : "#DCDCE1") : hover.hovered ? Theme.fill : "transparent"
    activeFocusOnTab: true

    Accessible.role: Accessible.PageTab
    Accessible.name: label
    Accessible.selected: current
    Accessible.onPressAction: activated()
    Keys.onReturnPressed: activated()
    Keys.onSpacePressed: activated()

    Behavior on color { ColorAnimation { duration: Theme.dur(120) } }

    Icon {
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        name: item.icon
        color: item.current ? Theme.accent : Theme.textSecondary
    }

    AppText {
        anchors.left: parent.left
        anchors.leftMargin: 38
        anchors.verticalCenter: parent.verticalCenter
        text: item.label
        font.weight: item.current ? Font.Medium : Font.Normal
    }

    Rectangle {
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        visible: item.badge > 0
        width: Math.max(20, count.implicitWidth + 12)
        height: 20
        radius: 10
        color: Theme.accent

        AppText {
            id: count
            anchors.centerIn: parent
            text: item.badge
            color: "#FFFFFF"
            font.pixelSize: Theme.smallSize
            font.weight: Font.DemiBold
        }
    }

    HoverHandler { id: hover }
    TapHandler { onTapped: item.activated() }
    FocusRing { }
}
