pragma Singleton
import QtQuick

QtObject {
    readonly property bool dark: Qt.styleHints.colorScheme === Qt.Dark
    property bool reduceMotion: false

    readonly property color window: dark ? "#1C1C1E" : "#FBFBFD"
    readonly property color sidebar: dark ? "#252527" : "#EFEFF2"
    readonly property color card: dark ? "#2C2C2E" : "#FFFFFF"
    readonly property color field: dark ? "#2C2C2E" : "#FFFFFF"
    readonly property color fill: dark ? "#3A3A3C" : "#E8E8ED"
    readonly property color fillHover: dark ? "#48484A" : "#DEDEE3"
    readonly property color separator: dark ? "#3A3A3C" : "#E5E5EA"
    readonly property color text: dark ? "#F5F5F7" : "#1D1D1F"
    readonly property color textSecondary: dark ? "#A1A1A6" : "#6E6E73"
    readonly property color accent: dark ? "#0A84FF" : "#0071E3"
    readonly property color accentHover: dark ? "#409CFF" : "#0077ED"
    readonly property color positive: dark ? "#30D158" : "#1E8E3E"
    readonly property color negative: dark ? "#FF6961" : "#D70015"
    readonly property color scrim: dark ? "#99000000" : "#55000000"
    readonly property color shadow: dark ? "#66000000" : "#1F000000"

    readonly property string textFont: "Segoe UI Variable Text"
    readonly property string displayFont: "Segoe UI Variable Display"
    readonly property int bodySize: 14
    readonly property int smallSize: 12

    function dur(milliseconds) {
        return reduceMotion ? 0 : milliseconds
    }
}
