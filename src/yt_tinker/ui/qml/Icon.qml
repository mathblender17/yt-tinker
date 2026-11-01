import QtQuick
import QtQuick.Window

// Icons are from Lucide (https://lucide.dev), ISC License, Copyright (c) Lucide Contributors.
Image {
    id: icon

    property string name
    property color color: Theme.textSecondary
    property real size: 18

    readonly property var shapes: ({
        "search": "<circle cx='11' cy='11' r='8' /><path d='m21 21-4.3-4.3' />",
        "download": "<path d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4' /><polyline points='7 10 12 15 17 10' /><line x1='12' x2='12' y1='15' y2='3' />",
        "library": "<path d='m16 6 4 14' /><path d='M12 6v14' /><path d='M8 8v12' /><path d='M4 4v16' />",
        "music": "<path d='M9 18V5l12-2v13' /><circle cx='6' cy='18' r='3' /><circle cx='18' cy='16' r='3' />",
        "video": "<path d='m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5' /><rect x='2' y='6' width='14' height='12' rx='2' />",
        "settings": "<path d='M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z' /><circle cx='12' cy='12' r='3' />",
        "pause": "<rect x='14' y='4' width='4' height='16' rx='1' /><rect x='6' y='4' width='4' height='16' rx='1' />",
        "play": "<polygon points='6 3 20 12 6 21 6 3' />",
        "x": "<path d='M18 6 6 18' /><path d='m6 6 12 12' />",
        "rotate-cw": "<path d='M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8' /><path d='M21 3v5h-5' />",
        "folder-open": "<path d='m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2' />",
        "check": "<path d='M20 6 9 17l-5-5' />",
        "circle-alert": "<circle cx='12' cy='12' r='10' /><line x1='12' x2='12' y1='8' y2='12' /><line x1='12' x2='12.01' y1='16' y2='16' />",
        "list-music": "<path d='M21 15V6' /><path d='M18.5 18a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z' /><path d='M12 12H3' /><path d='M16 6H3' /><path d='M12 18H3' />",
        "trash-2": "<path d='M3 6h18' /><path d='M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6' /><path d='M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2' /><line x1='10' x2='10' y1='11' y2='17' /><line x1='14' x2='14' y1='11' y2='17' />",
        "arrow-down-to-line": "<path d='M12 17V3' /><path d='m6 11 6 6 6-6' /><path d='M19 21H5' />"
    })

    width: size
    height: size
    sourceSize: Qt.size(Math.ceil(size * Screen.devicePixelRatio), Math.ceil(size * Screen.devicePixelRatio))
    fillMode: Image.PreserveAspectFit
    source: name
        ? "data:image/svg+xml," + encodeURIComponent(
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='"
            + color + "' stroke-width='1.75' stroke-linecap='round' stroke-linejoin='round'>"
            + shapes[name] + "</svg>")
        : ""
}
