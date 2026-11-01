import QtQuick

Column {
    property string icon
    property string title
    property string message

    anchors.centerIn: parent
    spacing: 10

    Icon {
        anchors.horizontalCenter: parent.horizontalCenter
        name: parent.icon
        size: 36
    }

    AppText {
        anchors.horizontalCenter: parent.horizontalCenter
        text: parent.title
        font.pixelSize: 17
        font.weight: Font.DemiBold
    }

    AppText {
        anchors.horizontalCenter: parent.horizontalCenter
        text: parent.message
        color: Theme.textSecondary
    }
}
