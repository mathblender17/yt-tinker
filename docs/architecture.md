# Architecture

YT Tinker uses four directional layers: **UI → application services → domain →
infrastructure adapters**. Imports flow inward; domain objects do not import Qt or
yt-dlp, and the UI does not call yt-dlp.

`QueueManager` owns queue ordering and legal state transitions. `DownloadService`
orchestrates one active request through a downloader protocol. `SearchService` accepts
a provider protocol so a future catalog or library provider can coexist with yt-dlp.
`SettingsService` persists preferences through a platformdirs-backed JSON adapter.

Playlist requests remain a single `QueueItem`. A downloader reports child completion
and active-child progress, allowing the queue to calculate aggregate progress without
creating a row for every video. Successful downloader results are `MediaItem` records,
which can later feed a local media library without adding a database today.
