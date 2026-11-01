import QtQuick
import QtQuick.Effects

Item {
    id: thumbnail

    property url source
    property real radius: 8
    property int pixelWidth: 640
    property string fallbackIcon: "video"

    Rectangle {
        anchors.fill: parent
        radius: thumbnail.radius
        color: Theme.fill

        Icon {
            anchors.centerIn: parent
            visible: image.status !== Image.Ready
            name: thumbnail.fallbackIcon
            size: Math.min(parent.height * 0.4, 28)
        }
    }

    Image {
        id: image
        anchors.fill: parent
        visible: false
        source: thumbnail.source
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        sourceSize.width: thumbnail.pixelWidth
    }

    Item {
        id: mask
        anchors.fill: parent
        visible: false
        layer.enabled: true
        layer.smooth: true

        Rectangle {
            anchors.fill: parent
            radius: thumbnail.radius
        }
    }

    MultiEffect {
        anchors.fill: parent
        source: image
        maskEnabled: true
        maskSource: mask
        maskThresholdMin: 0.5
        maskSpreadAtMin: 1
        opacity: image.status === Image.Ready ? 1 : 0

        Behavior on opacity { NumberAnimation { duration: Theme.dur(220) } }
    }
}
