# YT Tinker

YT Tinker is a Windows-first personal media downloader built around a responsive queue.
This repository is a greenfield rebuild; the previous executable is only a visual and
behavioral reference.

## Development

Install Python 3.12 or newer, then create an environment and install the project:

```powershell
uv venv --python 3.12
uv sync --extra dev
uv run yt-tinker
```

Run the offline test suite and quality checks:

```powershell
uv run pytest
uv run ruff check .
uv run mypy
```

FFmpeg is deliberately not bundled or downloaded by the application. Install it and add
it to `PATH` before using video merging or MP3 extraction.

## Current phase

Phase 2 supplies the launchable application shell, domain models, settings storage,
dependency diagnostics, and tested queue/foundation utilities. Download execution and
search UI behavior are implemented in later phases.
