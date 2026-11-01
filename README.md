# YT Tinker

A personal YouTube video and music downloader for Windows 11. Paste a link or search, then
save as MP4 or MP3.

- **Fast:** downloads over parallel HLS fragments, which beat single-connection HTTPS
  by about 3× in testing, and a link preview's metadata is reused rather than fetched twice.
- **Files that work everywhere:** H.264/AAC MP4 up to 1080p by default, with a Maximum
  option up to 4K. MP3s get square cover art and tags.
- **A real queue:** three downloads at once, with pause, resume and retry. Unfinished work
  comes back after a restart, and partial files stay out of your media folders.
- **Playlists:** each video gets its own row and retry, saved to a numbered subfolder.

## Install

You need Python 3.14 from python.org, [uv](https://docs.astral.sh/uv/),
[FFmpeg](https://ffmpeg.org), and [Deno](https://deno.com) or Node.js, with the last three
on `PATH`. Then run:

```powershell
.\packaging\install.ps1
```

This installs the app to `%LOCALAPPDATA%\Programs\YT Tinker` and adds a **YT Tinker** shortcut
to your desktop. Rerun it to apply code changes or to update yt-dlp, which is the first thing
to try if downloads stop working. Close the app first.

There's no standalone `.exe` on purpose: Windows Smart App Control blocks unsigned
executables it doesn't recognize, so the app runs on Python's signed `pythonw.exe` instead.

Downloads go to `Downloads\YT Tinker` until you change it in Settings, split into `Video`
and `Audio` folders.

Shortcuts: `Ctrl+1` to `Ctrl+4` switch pages, and `Ctrl+L` jumps to the search field.

## Develop

```powershell
uv sync --extra dev
uv run yt-tinker
uv run pytest
uv run ruff check .
uv run mypy
```

Icons are from [Lucide](https://lucide.dev) (ISC License).
