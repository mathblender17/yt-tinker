import QtQuick
import QtQuick.Effects

Item {
    id: field

    property alias text: input.text
    property string placeholder
    property int fieldHeight: 46
    property bool busy: false

    signal submitted()

    function focusInput() {
        input.forceActiveFocus()
        input.selectAll()
    }

    implicitHeight: fieldHeight

    RectangularShadow {
        anchors.fill: box
        radius: box.radius
        blur: input.activeFocus ? 24 : 12
        offset.y: 2
        color: Theme.shadow

        Behavior on blur { NumberAnimation { duration: Theme.dur(160) } }
    }

    Rectangle {
        id: box
        anchors.fill: parent
        radius: 12
        color: Theme.field
        border.width: input.activeFocus ? 2 : 0
        border.color: Theme.accent
    }

    Icon {
        id: searchIcon
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        name: "search"
    }

    TextInput {
        id: input
        anchors.left: searchIcon.right
        anchors.leftMargin: 10
        anchors.right: clear.visible ? clear.left : parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        color: Theme.text
        selectionColor: Theme.accent
        selectedTextColor: "#FFFFFF"
        selectByMouse: true
        clip: true
        font.family: Theme.textFont
        font.pixelSize: 15

        Accessible.role: Accessible.EditableText
        Accessible.name: field.placeholder

        Keys.onReturnPressed: field.submitted()
        Keys.onEnterPressed: field.submitted()
        Keys.onEscapePressed: input.text = ""

        AppText {
            anchors.fill: parent
            visible: !input.text
            text: field.placeholder
            color: Theme.textSecondary
            font.pixelSize: 15
        }
    }

    IconButton {
        id: clear
        anchors.right: parent.right
        anchors.rightMargin: 7
        anchors.verticalCenter: parent.verticalCenter
        visible: input.text !== ""
        icon: "x"
        label: "Clear"
        onClicked: {
            input.text = ""
            input.forceActiveFocus()
        }
    }

    Rectangle {
        anchors.left: box.left
        anchors.right: box.right
        anchors.bottom: box.bottom
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        height: 2
        radius: 1
        color: Theme.accent
        visible: field.busy

        SequentialAnimation on opacity {
            running: field.busy
            loops: Animation.Infinite
            NumberAnimation { from: 0.15; to: 1; duration: 520; easing.type: Easing.InOutSine }
            NumberAnimation { from: 1; to: 0.15; duration: 520; easing.type: Easing.InOutSine }
        }
    }
}
