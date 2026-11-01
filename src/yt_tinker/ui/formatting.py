from __future__ import annotations


def human_size(size: float | None) -> str:
    if size is None:
        return "—"
    for unit in ("B", "KB", "MB"):
        if size < 1000:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1000
    return f"{size:.2f} GB"


def human_speed(bytes_per_second: float) -> str:
    return f"{human_size(bytes_per_second)}/s"


def human_eta(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} sec left"
    if seconds < 3600:
        return f"{round(seconds / 60)} min left"
    return f"{seconds // 3600} hr {seconds % 3600 // 60} min left"


def human_duration(seconds: float | None) -> str:
    if not seconds:
        return ""
    minutes, remainder = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{remainder:02d}" if hours else f"{minutes}:{remainder:02d}"


def human_views(count: int | None) -> str:
    if not count:
        return ""
    if count < 1000:
        return f"{count} views"
    for limit, suffix in ((1_000_000, "K"), (1_000_000_000, "M")):
        if count < limit:
            value = count / (limit / 1000)
            return f"{value:.0f}{suffix} views" if value >= 10 else f"{value:.1f}{suffix} views"
    return f"{count / 1_000_000_000:.1f}B views"
