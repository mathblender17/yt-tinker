import QtQuick

Rectangle {
    id: control

    property var options: []  // [{ label, value }]
    property string value
    readonly property int selected: Math.max(0, options.findIndex(option => option.value === value))
    readonly property real segmentWidth: width / Math.max(1, options.length)

    signal activated(string value)

    implicitWidth: options.length * 92
    implicitHeight: 32
    radius: 8
    color: Theme.fill
    activeFocusOnTab: true

    Accessible.role: Accessible.PageTabList
    Keys.onLeftPressed: step(-1)
    Keys.onRightPressed: step(1)

    function step(delta) {
        const next = (selected + delta + options.length) % options.length
        activated(options[next].value)
    }

    Rectangle {
        x: 2 + control.selected * control.segmentWidth
        y: 2
        width: control.segmentWidth - 4
        height: parent.height - 4
        radius: 6
        color: Theme.dark ? "#636366" : "#FFFFFF"

        Behavior on x { SpringAnimation { spring: 5; damping: 0.42; epsilon: 0.25; duration: Theme.dur(240) } }
    }

    Row {
        anchors.fill: parent

        Repeater {
            model: control.options

            Item {
                required property var modelData
                width: control.segmentWidth
                height: control.height

                Accessible.role: Accessible.PageTab
                Accessible.name: modelData.label

                AppText {
                    anchors.fill: parent
                    horizontalAlignment: Text.AlignHCenter
                    text: parent.modelData.label
                    font.pixelSize: 13
                    font.weight: parent.modelData.value === control.value ? Font.Medium : Font.Normal
                }

                TapHandler { onTapped: control.activated(parent.modelData.value) }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
            }
        }
    }

    FocusRing { }
}
