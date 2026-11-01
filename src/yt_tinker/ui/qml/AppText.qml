import QtQuick

// PlainText always: titles come from the internet and must never render as markup.
Text {
    color: Theme.text
    textFormat: Text.PlainText
    font.family: Theme.textFont
    font.pixelSize: Theme.bodySize
    elide: Text.ElideRight
    verticalAlignment: Text.AlignVCenter
}
