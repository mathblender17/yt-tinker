# Architecture

YT Tinker uses four directional layers: **UI → application services → domain →
infrastructure adapters**. Domain objects do not import Qt or yt-dlp, and the UI does not
call yt-dlp.

`QueueManager` owns queue ordering, legal state transitions and the limit of three active
downloads. `DownloadService` runs one request through a downloader protocol and turns
backend failures into domain errors. `SearchService` wraps a provider protocol and caches
results. `SettingsService` persists preferences through a JSON adapter, and `QueueStore`
saves unfinished work the same way.

The UI is Qt Quick. `ui/bridge.py` is the only object QML talks to: it owns the list models,
starts one `DownloadWorker` thread per download, and runs searches on the thread pool. Each
`QML` file in `ui/qml` is one component, and `Theme.qml` holds every color and duration.

Playlists expand into one `QueueItem` per video when added, so each video gets parallelism,
progress and retry from the normal queue. `DownloadRequest.collection` and `index` keep them
together in a subfolder.

## Why downloads look the way they do

These come from timing real downloads on this project's connection:

- HLS with parallel fragments beats direct HTTPS, which holds at about 1 MB/s per
  connection. 16 connections was the best setting; 48 cut throughput in half, so parallel
  downloads share a budget of about 32.
- `http_chunk_size` made direct HTTPS slower, so it stays off.
- yt-dlp's cancel only reaches a fragment after that fragment opens a connection, so
  `urlopen` is wrapped to fail fast. That took cancelling from 13s to under 2s.
- yt-dlp probes dozens of thumbnail URLs for MP3 covers, so the list is cut to three.
- Partial files live in `.partial/<hash>` beside the output, so a cancelled download can be
  deleted cleanly and the media folder only ever holds finished files.

## Why it isn't a PyInstaller .exe

A PyInstaller build was tried first and dropped. Smart App Control judges unknown unsigned
executables by reputation, and one build of the same code passed while the next was blocked.
A self-signed certificate wouldn't change that. `packaging/install.ps1` instead creates an
environment on the Python Software Foundation's signed build, and the desktop shortcut starts
its `pythonw.exe`, so the app installs without depending on this folder.

Stay on a stock Python for this. A PyInstaller build from `.venv` also failed on every HTTPS
request, because that environment's base Python patches `ssl.py` to read a file that wasn't
bundled.
