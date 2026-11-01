from __future__ import annotations

import importlib.metadata
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    name: str
    available: bool
    detail: str


def collect_dependency_status() -> list[DependencyStatus]:
    return [
        _python_package("yt-dlp"),
        _executable("FFmpeg", "ffmpeg"),
        _javascript_runtime(),
    ]


def _python_package(package: str) -> DependencyStatus:
    try:
        return DependencyStatus(package, True, f"Version {importlib.metadata.version(package)}")
    except importlib.metadata.PackageNotFoundError:
        return DependencyStatus(package, False, "Install the Python package.")


def _executable(label: str, executable: str) -> DependencyStatus:
    path = shutil.which(executable)
    return DependencyStatus(label, path is not None, path or f"{executable} was not found on PATH.")


def _javascript_runtime() -> DependencyStatus:
    for executable in ("deno", "node", "bun"):
        path = shutil.which(executable)
        if path:
            try:
                version = (
                    subprocess.run(
                        [path, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=3,
                        check=False,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    .stdout.strip()
                    .splitlines()[0]
                )
                return DependencyStatus("JavaScript runtime", True, f"{executable}: {version}")
            except (OSError, subprocess.SubprocessError, IndexError):
                continue
    return DependencyStatus(
        "JavaScript runtime",
        False,
        "Install a supported Node.js, Deno, or Bun runtime and add it to PATH.",
    )
