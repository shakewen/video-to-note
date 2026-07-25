import json
import re
from html import escape
from pathlib import Path
from typing import Any


def format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def draft_chapters_from_transcript(
    transcript_json_path: Path,
    chapter_seconds: int = 300,
    max_gap_seconds: int = 45,
    include_frames: bool = False,
) -> list[dict[str, Any]]:
    data = json.loads(transcript_json_path.read_text(encoding="utf-8-sig"))
    return draft_chapters_from_segments(
        data.get("segments", []),
        chapter_seconds=chapter_seconds,
        max_gap_seconds=max_gap_seconds,
        include_frames=include_frames,
    )


def draft_chapters_from_segments(
    segments: list[dict[str, Any]],
    chapter_seconds: int = 300,
    max_gap_seconds: int = 45,
    include_frames: bool = False,
) -> list[dict[str, Any]]:
    normalized = _normalize_segments(segments)
    if not normalized:
        raise ValueError("transcript segments are required")

    groups = _group_segments(normalized, chapter_seconds, max_gap_seconds)
    return [_draft_chapter(group, include_frames) for group in groups]


def write_draft_chapters(
    transcript_json_path: Path,
    output_path: Path,
    chapter_seconds: int = 300,
    max_gap_seconds: int = 45,
    include_frames: bool = False,
) -> None:
    chapters = draft_chapters_from_transcript(
        transcript_json_path,
        chapter_seconds=chapter_seconds,
        max_gap_seconds=max_gap_seconds,
        include_frames=include_frames,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"chapters": chapters}, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        normalized.append(
            {
                "start": float(segment.get("start", 0.0)),
                "end": float(segment.get("end", segment.get("start", 0.0))),
                "text": text,
            }
        )
    return sorted(normalized, key=lambda item: item["start"])


def _group_segments(
    segments: list[dict[str, Any]],
    chapter_seconds: int,
    max_gap_seconds: int,
) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for segment in segments:
        if current:
            gap = segment["start"] - current[-1]["end"]
            duration = segment["end"] - current[0]["start"]
            if gap > max_gap_seconds or duration > chapter_seconds:
                groups.append(current)
                current = []
        current.append(segment)
    if current:
        groups.append(current)
    return groups


def _draft_chapter(group: list[dict[str, Any]], include_frames: bool) -> dict[str, Any]:
    start = group[0]["start"]
    end = max(segment["end"] for segment in group)
    combined_text = " ".join(segment["text"] for segment in group)
    title = _pick_title(combined_text)
    quote = _short_quote(combined_text)
    midpoint = (start + end) / 2

    chapter: dict[str, Any] = {
        "title": title,
        "time_range": f"{format_timestamp(start)}-{format_timestamp(end)}",
        "body": [
            f"问题：这一段围绕“{title}”展开，需要结合画面确认真实意图。",
            f"步骤：先根据转写核对这句原话：“{quote}”。",
            "陷阱：这是自动草稿，不能直接交付；需要人工补充本章真实误区和结论。",
            "结论：精修时把这一章改成白话短句，并保留可回跳时间戳。",
        ],
        "quote": quote,
        "visual_anchor": f"{format_timestamp(midpoint)} 请从本章画面中挑一个最清晰的信息点。",
        "diagram_type": "flow",
        "svg": _draft_svg(title),
        "needs_review": True,
    }
    if include_frames:
        chapter["frame"] = {
            "src": f"./frames/{_safe_file_stem(title)}_{int(midpoint)}s.jpg",
            "timestamp": format_timestamp(midpoint),
        }
    return chapter


def _pick_title(text: str) -> str:
    words = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_-]+", text)
    if not words:
        return "待命名章节"
    word = words[0]
    word = re.sub(r"^(先|再|然后|接下来|这里的|这里|现在|首先)", "", word)
    return word[:10] or words[0][:10]


def _short_quote(text: str, max_chars: int = 48) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:max_chars]


def _draft_svg(title: str) -> str:
    label = escape(title)
    return (
        '<svg viewBox="0 0 360 120" role="img" aria-label="章节草稿图解">'
        '<rect x="18" y="36" width="118" height="46" rx="6" fill="#e7f2f4" stroke="#256d85"/>'
        f'<text x="34" y="64" font-size="14">步骤1 {label}</text>'
        '<line x1="142" y1="59" x2="218" y2="59" stroke="#256d85" stroke-width="2"/>'
        '<polygon points="218,59 208,54 208,64" fill="#256d85"/>'
        '<rect x="224" y="36" width="118" height="46" rx="6" fill="#fff" stroke="#256d85"/>'
        '<text x="240" y="64" font-size="14">步骤2 人工精修</text>'
        '</svg>'
    )


def _safe_file_stem(text: str) -> str:
    stem = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text, flags=re.UNICODE).strip("_")
    return stem or "chapter"
