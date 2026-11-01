import QtQuick
import QtQuick.Effects

Item {
    id: toast

    property bool showing: false
    property string message

    function show(text) {
        message = text
        showing = true
        hideTimer.restart()
    }

    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: parent.bottom
    anchors.bottomMargin: showing ? 24 : 8
    width: pill.width
    height: pill.height
    opacity: showing ? 1 : 0

    Accessible.role: Accessible.AlertMessage
    Accessible.name: message

    Behavior on anchors.bottomMargin { SpringAnimation { spring: 4; damping: 0.45; epsilon: 0.25; duration: Theme.dur(300) } }
    Behavior on opacity { NumberAnimation { duration: Theme.dur(160) } }

    Timer {
        id: hideTimer
        interval: 2600
        onTriggered: toast.showing = false
    }

    RectangularShadow {
        anchors.fill: pill
        radius: pill.radius
        blur: 20
        offset.y: 4
        color: Theme.shadow
    }

    Rectangle {
        id: pill
        width: label.implicitWidth + 32
        height: 38
        radius: 19
        color: Theme.dark ? "#3A3A3C" : "#1D1D1F"

        AppText {
            id: label
            anchors.centerIn: parent
            text: toast.message
            color: "#FFFFFF"
            font.pixelSize: 13
            font.weight: Font.Medium
        }
    }
}
