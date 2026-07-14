from pathlib import Path, PurePosixPath
import re
from typing import Any

from .commands import build_frame_command, format_command


def frame_commands_from_chapters(
    chapters: list[dict[str, Any]],
    video_path: str,
    html_dir: Path,
) -> list[list[str]]:
    commands = []
    for index, chapter in enumerate(chapters, start=1):
        frame = chapter.get("frame")
        if not isinstance(frame, dict):
            continue
        timestamp = str(frame.get("timestamp", "")).strip()
        src = str(frame.get("src", "")).strip()
        if not timestamp or not src:
            continue
        output_path = _resolve_html_relative_frame(src, html_dir)
        commands.append(build_frame_command(video_path, timestamp, str(output_path)))
    return commands


def plan_frame_commands(
    chapters: list[dict[str, Any]],
    video_path: str,
    html_dir: Path,
) -> str:
    commands = frame_commands_from_chapters(chapters, video_path, html_dir)
    lines = ["# Frame Extraction Commands", ""]
    if not commands:
        lines.append("No chapter frame definitions found.")
    else:
        lines.extend(f"`{format_command(command)}`" for command in commands)
    return "\n".join(lines) + "\n"


def candidate_frame_commands_from_chapters(
    chapters: list[dict[str, Any]],
    video_path: str,
    html_dir: Path,
    every_seconds: int = 30,
    max_per_chapter: int = 6,
) -> list[list[str]]:
    commands = []
    for index, chapter in enumerate(chapters, start=1):
        time_range = str(chapter.get("time_range", "")).strip()
        parsed = _parse_time_range(time_range)
        if not parsed:
            continue
        start, end = parsed
        timestamps = _candidate_seconds(start, end, every_seconds, max_per_chapter)
        title = _safe_file_stem(str(chapter.get("title") or f"chapter_{index}"))
        for candidate_index, seconds in enumerate(timestamps, start=1):
            output_path = (
                html_dir
                / "frames"
                / "candidates"
                / f"{title}_{int(seconds)}s_candidate{candidate_index:02d}.jpg"
            )
            commands.append(build_frame_command(video_path, _format_seconds(seconds), str(output_path)))
    return commands


def plan_candidate_frame_commands(
    chapters: list[dict[str, Any]],
    video_path: str,
    html_dir: Path,
    every_seconds: int = 30,
    max_per_chapter: int = 6,
) -> str:
    commands = candidate_frame_commands_from_chapters(
        chapters,
        video_path,
        html_dir,
        every_seconds=every_seconds,
        max_per_chapter=max_per_chapter,
    )
    lines = [
        "# Candidate Frame Commands",
        "",
        "Run these ffmpeg commands before choosing final chapter screenshots.",
        "Review these candidates, then copy the best timestamp into each chapter frame entry.",
        "",
    ]
    if not commands:
        lines.append("No chapter time ranges found.")
    else:
        lines.extend(f"`{format_command(command)}`" for command in commands)
    return "\n".join(lines) + "\n"


def _resolve_html_relative_frame(src: str, html_dir: Path) -> Path:
    normalized = src.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    # Treat chapter frame paths as HTML-relative so offline references keep working.
    return html_dir / Path(PurePosixPath(normalized))


def _candidate_seconds(start: int, end: int, every_seconds: int, max_per_chapter: int) -> list[int]:
    interval = max(1, every_seconds)
    limit = max(1, max_per_chapter)
    if end < start:
        return []
    seconds = []
    current = start
    while current <= end and len(seconds) < limit:
        seconds.append(current)
        current += interval
    return seconds


def _parse_time_range(value: str) -> tuple[int, int] | None:
    parts = re.split(r"\s*-\s*", value, maxsplit=1)
    if len(parts) != 2:
        return None
    start = _parse_timestamp(parts[0])
    end = _parse_timestamp(parts[1])
    if start is None or end is None:
        return None
    return start, end


def _parse_timestamp(value: str) -> int | None:
    parts = value.strip().split(":")
    if len(parts) not in {2, 3}:
        return None
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return None
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def _format_seconds(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _safe_file_stem(text: str) -> str:
    stem = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text, flags=re.UNICODE).strip("_")
    return stem or "chapter"
