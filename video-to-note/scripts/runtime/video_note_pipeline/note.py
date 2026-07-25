import json
import os
from pathlib import Path

from .chapters import load_chapters_json, validate_chapters
from .actionable import validate_actionable_payload
from .actionable_html import render_actionable_html
from .cognitive_html import render_cognitive_html
from .html import render_html
from .metadata import summarize_metadata


LOCAL_THUMBNAIL_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def render_note_html(
    metadata_json_path: Path,
    chapters_json_path: Path,
    require_frames: bool = False,
    output_html_path: Path | None = None,
) -> str:
    metadata = json.loads(metadata_json_path.read_text(encoding="utf-8-sig"))
    summary = summarize_metadata(metadata)
    _prefer_local_thumbnail(summary, metadata_json_path, output_html_path)
    raw_chapters = json.loads(chapters_json_path.read_text(encoding="utf-8-sig"))
    if isinstance(raw_chapters, dict) and raw_chapters.get("schema_version") == 3:
        validate_actionable_payload(raw_chapters, require_frames=require_frames)
        return render_actionable_html(str(summary["title"]), summary, raw_chapters)
    chapters = load_chapters_json(chapters_json_path)
    validate_chapters(chapters, require_frames=require_frames)
    if any(chapter.get("template_type") for chapter in chapters):
        return render_cognitive_html(str(summary["title"]), summary, chapters)
    return render_html(str(summary["title"]), summary, chapters)


def _prefer_local_thumbnail(summary: dict, metadata_json_path: Path, output_html_path: Path | None) -> None:
    if not output_html_path:
        return
    local_thumbnail = _find_local_thumbnail(metadata_json_path.parent)
    if not local_thumbnail:
        return
    relative_path = os.path.relpath(local_thumbnail, start=output_html_path.parent)
    summary["thumbnail"] = relative_path.replace(os.sep, "/")


def _find_local_thumbnail(metadata_dir: Path) -> Path | None:
    if not metadata_dir.is_dir():
        return None
    candidates = [
        path
        for path in metadata_dir.iterdir()
        if path.is_file() and path.suffix.lower() in LOCAL_THUMBNAIL_EXTENSIONS
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: path.name.lower())[0]
