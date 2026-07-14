import json
import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any


class ChapterValidationError(ValueError):
    pass


RELATIONSHIP_MARKERS = (
    "<line",
    "<path",
    "<polyline",
    "<polygon",
    "marker-end",
    "marker-start",
    "→",
    "->",
)

DIAGRAM_TYPE_MARKERS = {
    "flow": ("步骤", "流程", "路径", "step", "flow", "1.", "2.", "步骤1", "步骤2"),
    "concept": ("概念", "关系", "层级", "分层", "包含", "属于", "concept", "layer"),
    "timeline": ("时间", "阶段", "之前", "之后", "timeline", "phase"),
    "matrix": ("对比", "矩阵", "优点", "缺点", "差异", "matrix", "vs"),
    "checklist": ("检查", "清单", "风险", "误区", "确认", "check", "risk", "✓"),
    "decision_tree": ("是否", "如果", "决策", "分支", "decision", "?"),
    "data": ("数据", "比例", "数量", "趋势", "指标", "%", "data"),
    "causal": ("原因", "结果", "导致", "影响", "因果", "because", "cause"),
}


def validate_chapters(chapters: list[dict[str, Any]], require_frames: bool = False) -> dict[str, Any]:
    if not chapters:
        raise ChapterValidationError("at least one chapter is required")

    seen_svg = set()
    for index, chapter in enumerate(chapters, start=1):
        _validate_required_text(chapter, index)
        if str(chapter.get("template_type", "")) == "brief":
            if str(chapter.get("diagram_type", "")) != "none" or str(chapter.get("svg", "")).strip():
                raise ChapterValidationError(f"chapter {index} brief template must not contain svg")
        else:
            _validate_svg(chapter, index, seen_svg)
        if require_frames:
            _validate_frame(chapter, index)

    return {"status": "ok", "chapter_count": len(chapters)}


def load_chapters_json(path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict) and isinstance(data.get("chapters"), list):
        return data["chapters"]
    if isinstance(data, list):
        return data
    raise ChapterValidationError("chapters JSON must be a list or an object with a chapters list")


def _validate_required_text(chapter: dict[str, Any], index: int) -> None:
    for key in ("title", "time_range", "body", "visual_anchor"):
        if not chapter.get(key):
            raise ChapterValidationError(f"chapter {index} missing {key}")
    body = chapter.get("body")
    if not isinstance(body, list) or not all(str(item).strip() for item in body):
        raise ChapterValidationError(f"chapter {index} body must be a non-empty list of text")


def _validate_svg(chapter: dict[str, Any], index: int, seen_svg: set[str]) -> None:
    svg = str(chapter.get("svg", "")).strip()
    if "<svg" not in svg or "</svg>" not in svg:
        raise ChapterValidationError(f"chapter {index} svg must be inline SVG")
    if not any(marker in svg for marker in RELATIONSHIP_MARKERS):
        raise ChapterValidationError(f"chapter {index} svg must contain a relationship marker")
    _validate_diagram_type(chapter, svg, index)

    keywords = _chapter_keywords(chapter)
    if not any(keyword and keyword in svg for keyword in keywords):
        raise ChapterValidationError(f"chapter {index} svg must contain a chapter keyword")

    normalized = _normalize_svg(svg)
    if normalized in seen_svg:
        raise ChapterValidationError(f"chapter {index} svg duplicates a previous chapter")
    seen_svg.add(normalized)


def _validate_diagram_type(chapter: dict[str, Any], svg: str, index: int) -> None:
    diagram_type = str(chapter.get("diagram_type") or chapter.get("svg_type") or "").strip()
    if not diagram_type:
        raise ChapterValidationError(f"chapter {index} missing diagram_type")
    if diagram_type not in DIAGRAM_TYPE_MARKERS:
        allowed = ", ".join(DIAGRAM_TYPE_MARKERS)
        raise ChapterValidationError(f"chapter {index} diagram_type must be one of: {allowed}")

    markers = DIAGRAM_TYPE_MARKERS[diagram_type]
    svg_lower = svg.lower()
    if not any(marker.lower() in svg_lower for marker in markers):
        raise ChapterValidationError(f"chapter {index} svg does not match diagram_type {diagram_type}")


def _validate_frame(chapter: dict[str, Any], index: int) -> None:
    frame = chapter.get("frame")
    if not isinstance(frame, dict):
        raise ChapterValidationError(f"chapter {index} frame is required")
    src = str(frame.get("src", "")).strip()
    timestamp = str(frame.get("timestamp", "")).strip()
    if not src:
        raise ChapterValidationError(f"chapter {index} frame src is required")
    if not timestamp:
        raise ChapterValidationError(f"chapter {index} frame timestamp is required")
    if _is_absolute_or_remote_path(src):
        raise ChapterValidationError(f"chapter {index} frame src must be a relative path")
    _validate_frame_timestamp_in_range(chapter, timestamp, index)


def _validate_frame_timestamp_in_range(chapter: dict[str, Any], timestamp: str, index: int) -> None:
    time_range = str(chapter.get("time_range", "")).strip()
    bounds = _parse_time_range_seconds(time_range)
    frame_second = _parse_timestamp_seconds(timestamp)
    if bounds is None or frame_second is None:
        raise ChapterValidationError(f"chapter {index} frame timestamp must match chapter time_range format")
    start, end = bounds
    if frame_second < start or frame_second > end:
        raise ChapterValidationError(f"chapter {index} frame timestamp is outside chapter time_range")


def _parse_time_range_seconds(value: str) -> tuple[int, int] | None:
    if "-" not in value:
        return None
    start_text, end_text = value.split("-", 1)
    start = _parse_timestamp_seconds(start_text.strip())
    end = _parse_timestamp_seconds(end_text.strip())
    if start is None or end is None or end < start:
        return None
    return start, end


def _parse_timestamp_seconds(value: str) -> int | None:
    parts = value.strip().split(":")
    if len(parts) not in (2, 3):
        return None
    if not all(part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def _chapter_keywords(chapter: dict[str, Any]) -> list[str]:
    title_words = re.findall(r"[\w\u4e00-\u9fff]+", str(chapter.get("title", "")))
    body_words = []
    for item in chapter.get("body", []):
        body_words.extend(re.findall(r"[\w\u4e00-\u9fff]+", str(item)))
    return [word for word in title_words + body_words if len(word) >= 2]


def _normalize_svg(svg: str) -> str:
    return re.sub(r"\s+", " ", svg).strip()


def _is_absolute_or_remote_path(path: str) -> bool:
    if path.startswith(("http://", "https://", "file://", "/", "\\")):
        return True
    if PureWindowsPath(path).is_absolute():
        return True
    return PurePosixPath(path).is_absolute()
