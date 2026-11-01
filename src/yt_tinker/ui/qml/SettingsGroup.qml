import QtQuick

Column {
    id: group

    property string title
    default property alias rows: card.data

    spacing: 8

    AppText {
        leftPadding: 2
        text: group.title
        font.pixelSize: 13
        font.weight: Font.DemiBold
        color: Theme.textSecondary
    }

    Rectangle {
        width: group.width
        height: card.implicitHeight
        radius: 12
        color: Theme.card

        Column {
            id: card
            width: parent.width
        }
    }
}
