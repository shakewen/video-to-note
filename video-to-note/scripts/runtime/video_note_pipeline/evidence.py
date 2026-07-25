"""Build a source-faithful evidence pack for downstream reasoning."""

from __future__ import annotations

import re
import math
from typing import Any


_TIME_RANGE = re.compile(
    r"^(?P<sh>\d{2,}):(?P<sm>\d{2}):(?P<ss>\d{2})-"
    r"(?P<eh>\d{2,}):(?P<em>\d{2}):(?P<es>\d{2})$"
)
_CHAPTER_FIELDS = (
    "chapter_index", "title", "time_range", "body", "detail_restoration",
    "key_quote", "template_type", "diagram_type", "frame", "visual_anchor",
)
_METADATA_FIELDS = (
    "id", "title", "uploader", "duration", "webpage_url", "description", "tags",
)
_MAIN_ROLES = {"main", "process", "step"}
_SIDE_ROLES = {"tip", "brief", "aside"}
_INDEPENDENT_ROLES = {"independent", "qa", "faq", "collection"}
_ACTION_WORDS = {
    "step", "prepare", "configure", "create", "edit", "run", "export", "first", "next", "then",
    "步骤", "首先", "然后", "接着", "配置", "创建", "编辑", "生成", "导出", "运行", "操作",
}
_INDEPENDENT_WORDS = {"faq", "q&a", "collection", "合集", "答疑", "独立", "问答"}


def _parse_time_range(value: Any) -> tuple[int, int]:
    if not isinstance(value, str):
        raise ValueError("chapter time_range must be a string")
    match = _TIME_RANGE.fullmatch(value)
    if not match:
        raise ValueError(f"invalid chapter time_range: {value!r}")
    values = {key: int(item) for key, item in match.groupdict().items()}
    if values["sm"] >= 60 or values["ss"] >= 60 or values["em"] >= 60 or values["es"] >= 60:
        raise ValueError(f"invalid chapter time_range: {value!r}")
    start = values["sh"] * 3600 + values["sm"] * 60 + values["ss"]
    end = values["eh"] * 3600 + values["em"] * 60 + values["es"]
    if end <= start:
        raise ValueError(f"chapter time_range must move forward: {value!r}")
    return start, end


def _chapter_text(chapter: dict[str, Any]) -> str:
    body = chapter.get("body")
    body_text = " ".join(str(item) for item in body) if isinstance(body, list) else str(body or "")
    return f"{chapter.get('title') or ''} {body_text}".lower()


def _has_main_relationship(chapters: list[dict[str, Any]], main_indexes: list[int]) -> tuple[bool, str]:
    required = len(main_indexes) // 2 + 1

    for field in ("project_goal", "course_goal", "deliverable_group"):
        counts: dict[str, int] = {}
        for index in main_indexes:
            value = chapters[index].get(field)
            if isinstance(value, str) and value.strip():
                counts[value] = counts.get(value, 0) + 1
        if counts and max(counts.values()) >= required:
            return True, f"多数主章节共享 {field}"

    orders = []
    for index in main_indexes:
        chapter = chapters[index]
        value = chapter.get("flow_order", chapter.get("order"))
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            continue
        orders.append(value)
    if len(orders) >= required and all(current == previous + 1 for previous, current in zip(orders, orders[1:])):
        return True, "多数主章节具有连续 flow_order/order"

    main_ids = {chapters[index].get("chapter_index") for index in main_indexes}
    depths: dict[Any, int] = {}
    longest = 0
    for index in main_indexes:
        chapter = chapters[index]
        chapter_id = chapter.get("chapter_index")
        raw_dependencies = chapter.get("depends_on", chapter.get("previous_step"))
        dependencies = raw_dependencies if isinstance(raw_dependencies, list) else [raw_dependencies]
        parent_depths = [depths[item] for item in dependencies if item in depths]
        depth = max(parent_depths, default=0) + 1
        if chapter_id in main_ids:
            depths[chapter_id] = depth
        longest = max(longest, depth)
    if longest >= required and longest > 1:
        return True, "depends_on/previous_step 依赖链覆盖多数主章节"
    return False, "未发现共同目标、连续顺序或多数依赖链"


def infer_topology_candidate(chapters: list[dict[str, Any]]) -> dict[str, str]:
    """Return a conservative topology candidate, never a final classification."""
    if not isinstance(chapters, list) or not chapters:
        raise ValueError("chapters must be a non-empty list")
    for index, chapter in enumerate(chapters):
        if not isinstance(chapter, dict):
            raise ValueError(f"chapter {index}: chapter must be an object")
        chapter_id = chapter.get("chapter_index")
        if isinstance(chapter_id, bool) or not isinstance(chapter_id, int) or chapter_id <= 0:
            raise ValueError(f"chapter {index}: chapter_index must be a positive integer")
        for field in ("template_type", "content_role", "flow_role"):
            value = chapter.get(field)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"chapter {index}: {field} must be a string")
        for field in ("flow_order", "order"):
            if field in chapter:
                value = chapter[field]
                if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                    raise ValueError(f"chapter {index}: {field} must be a positive integer")
        if "depends_on" in chapter:
            dependencies = chapter["depends_on"]
            if not isinstance(dependencies, list):
                raise ValueError(f"chapter {index}: depends_on must be a list")
            for dependency in dependencies:
                valid_integer = isinstance(dependency, int) and not isinstance(dependency, bool) and dependency > 0
                valid_string = isinstance(dependency, str) and bool(dependency.strip())
                if not (valid_integer or valid_string):
                    raise ValueError(
                        f"chapter {index}: depends_on elements must be non-empty strings or positive integers"
                    )
        if "previous_step" in chapter:
            previous = chapter["previous_step"]
            valid_integer = isinstance(previous, int) and not isinstance(previous, bool) and previous > 0
            valid_string = isinstance(previous, str) and bool(previous.strip())
            if not (valid_integer or valid_string):
                raise ValueError(f"chapter {index}: previous_step must be a non-empty string or positive integer")

    chapter_roles = [
        {
            str(chapter.get(field)).lower()
            for field in ("content_role", "flow_role")
            if chapter.get(field) is not None
        }
        for chapter in chapters
    ]
    main_count = sum(bool(roles & _MAIN_ROLES) for roles in chapter_roles)
    main_indexes = [index for index, roles in enumerate(chapter_roles) if roles & _MAIN_ROLES]
    side_count = sum(bool(roles & _SIDE_ROLES) for roles in chapter_roles)
    independent_count = sum(bool(roles & _INDEPENDENT_ROLES) for roles in chapter_roles)
    flow_count = sum(bool(roles & {"process", "step", "flow", "order", "stage"}) for roles in chapter_roles)
    texts = [_chapter_text(chapter) for chapter in chapters]
    action_count = sum(any(word in text for word in _ACTION_WORDS) for text in texts)
    independent_signal_count = sum(any(word in text for word in _INDEPENDENT_WORDS) for text in texts)
    brief_count = sum(chapter.get("template_type") == "brief" for chapter in chapters)
    sop_count = sum(chapter.get("template_type") in {"sop", "process", "step"} for chapter in chapters)
    count = len(chapters)
    tip_count = sum(
        bool(roles & _SIDE_ROLES) or chapter.get("template_type") == "brief"
        for roles, chapter in zip(chapter_roles, chapters)
    )
    tip_ratio = tip_count / count

    ranges = []
    ranges_valid = True
    for chapter in chapters:
        try:
            ranges.append(_parse_time_range(chapter.get("time_range")))
        except ValueError:
            ranges_valid = False
            break
    continuous = ranges_valid and all(
        current[0] >= previous[0] and -5 <= current[0] - previous[1] <= 120
        for previous, current in zip(ranges, ranges[1:])
    )
    has_relationship, relationship_reason = _has_main_relationship(chapters, main_indexes)

    if main_count == 0 and (independent_count + side_count >= (count + 1) // 2):
        candidate = "fragmented_knowledge"
        reason = f"候选，需 AI 确认：显式独立/答疑/tip/aside 角色占多数且无主流程角色（tip_ratio={tip_ratio:.2f}）。"
    elif tip_ratio >= 0.5 and main_count < count / 2:
        candidate = "fragmented_knowledge"
        reason = f"候选，需 AI 确认：tip/aside 比例较高（tip_ratio={tip_ratio:.2f}），主流程不足以形成连续课程。"
    elif independent_count + independent_signal_count >= max(2, (count + 1) // 2) and main_count == 0:
        candidate = "fragmented_knowledge"
        reason = f"候选，需 AI 确认：独立主题信号占优、无主流程角色且 tip_ratio={tip_ratio:.2f}。"
    elif main_count == count and side_count == 0 and continuous and has_relationship:
        candidate = "complete_course"
        reason = f"候选，需 AI 确认：全部为主流程角色、时间范围连续，且{relationship_reason}（tip_ratio={tip_ratio:.2f}）。"
    elif main_count > 0 and (side_count > 0 or brief_count > 0):
        candidate = "mixed_course"
        reason = f"候选，需 AI 确认：主流程与 tip/brief/aside 共存（tip_ratio={tip_ratio:.2f}）。"
    else:
        candidate = "mixed_course"
        reason = f"候选，需 AI 确认：{relationship_reason}，角色、模板及时间连续性不足以保守定类（tip_ratio={tip_ratio:.2f}）。"
    return {"type": candidate, "reason": reason}


def build_evidence_pack(
    metadata: dict[str, Any],
    transcript: dict[str, Any],
    cognitive_payload: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(cognitive_payload, dict):
        raise ValueError("cognitive_payload must be an object")
    chapters = cognitive_payload.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise ValueError("cognitive_payload.chapters must be a non-empty list")
    if not isinstance(transcript, dict):
        raise ValueError("transcript must be an object")
    segments = transcript.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("transcript.segments must be a non-empty list")

    validated_segments = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError(f"segment {index}: segment must be an object")
        for field in ("start", "end"):
            value = segment.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"segment {index}: {field} must be a number")
            if not math.isfinite(value):
                raise ValueError(f"segment {index}: {field} must be finite")
        if segment["start"] < 0:
            raise ValueError(f"segment {index}: start must be non-negative")
        if segment["end"] <= segment["start"]:
            raise ValueError(f"segment {index}: end must be greater than start")
        text = segment.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError(f"segment {index}: text must be a non-empty string")
        validated_segments.append(segment)

    evidence_chapters = []
    for chapter in chapters:
        if not isinstance(chapter, dict):
            raise ValueError("each chapter must be an object")
        start, end = _parse_time_range(chapter.get("time_range"))
        bound_segments = []
        for segment in validated_segments:
            segment_start = segment["start"]
            segment_end = segment["end"]
            text = segment["text"]
            overlaps = segment_end > start and segment_start < end
            if overlaps:
                bound_segments.append({"start": segment_start, "end": segment_end, "text": text})
        evidence = {field: chapter.get(field) for field in _CHAPTER_FIELDS}
        evidence.update({"start_seconds": start, "end_seconds": end, "segments": bound_segments})
        evidence_chapters.append(evidence)

    source_metadata = metadata if isinstance(metadata, dict) else {}
    compact_metadata = {field: source_metadata.get(field) for field in _METADATA_FIELDS}
    # None and [] explicitly mark absent source metadata; they are not inferred facts.
    if compact_metadata["tags"] is None:
        compact_metadata["tags"] = []
    return {
        "schema_version": 1,
        "topology_candidate": infer_topology_candidate(chapters),
        "chapters": evidence_chapters,
        "metadata": compact_metadata,
    }
