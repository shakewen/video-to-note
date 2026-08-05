from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from typing import Any
from urllib.parse import urlsplit


TOPOLOGY_TYPES = {
    "complete_course",
    "mixed_course",
    "fragmented_knowledge",
}
SOURCE_KINDS = {
    "video_source",
    "official_source",
    "third_party_source",
    "ai_teaching",
    "transfer_exercise",
    "needs_confirmation",
}

_UNIT_TYPES = {"operation", "concept", "brief"}
_TEMPLATE_TYPES = {"sop", "concept", "matrix", "brief"}
_DIAGRAM_TYPES = {"flow", "radial", "matrix", "none"}
_SUPPLEMENT_KINDS = {
    "ai_teaching",
    "official_source",
    "third_party_source",
    "needs_confirmation",
}
LEGACY_LEARNING_DESIGN_VERSION = "b-c-v1"
LEARNING_DESIGN_VERSION = "adaptive-blocks-v1"
SUPPORTED_LEARNING_DESIGN_VERSIONS = {
    LEGACY_LEARNING_DESIGN_VERSION,
    LEARNING_DESIGN_VERSION,
}
_ADAPTIVE_CHAPTER_ROLES = {
    "overview",
    "method",
    "decision",
    "process",
    "case",
    "warning",
    "conclusion",
}
_ADAPTIVE_BLOCK_TYPES = {
    "scope_facts",
    "case_reconstruction",
    "explanation",
    "process",
    "comparison",
    "limitations",
    "takeaway",
    "application",
    "observation",
    "summary",
}
_AI_ADVICE_VERDICTS = {
    "correct",
    "partially_correct",
    "incorrect",
    "insufficient_evidence",
}
NOTE_MODES = {"source-faithful"}


class ActionableValidationError(ValueError):
    pass


def prepare_actionable_skeleton(
    evidence_pack: dict[str, Any],
    note_mode: str = "source-faithful",
) -> dict[str, Any]:
    """Create an evidence-only schema v3 draft for the AI enrichment stage."""
    if not isinstance(evidence_pack, dict):
        raise ActionableValidationError("evidence pack 顶层必须是对象")
    chapters = evidence_pack.get("chapters")
    topology = evidence_pack.get("topology_candidate")
    if not isinstance(chapters, list) or not chapters:
        raise ActionableValidationError("evidence pack chapters 必须是非空列表")
    if not isinstance(topology, dict):
        raise ActionableValidationError("evidence pack topology_candidate 必须是对象")
    if note_mode not in NOTE_MODES:
        raise ActionableValidationError(f"note_mode 仅支持 {sorted(NOTE_MODES)}")

    prepared = [_actionable_chapter_skeleton(item, index) for index, item in enumerate(chapters, 1)]
    return {
        "schema_version": 3,
        "learning_design_version": LEARNING_DESIGN_VERSION,
        "note_mode": "source-faithful",
        "ai_advice_enabled": False,
        "content_topology": dict(topology),
        "learning_path": [],
        "chapters": prepared,
        "sources": [],
    }


def _actionable_chapter_skeleton(chapter: Any, fallback_index: int) -> dict[str, Any]:
    if not isinstance(chapter, dict):
        raise ActionableValidationError(f"evidence chapter {fallback_index} 必须是对象")
    index = chapter.get("chapter_index", fallback_index)
    template = str(chapter.get("template_type") or "")
    unit_type = "operation" if template == "sop" else "brief" if template == "brief" else "concept"
    body = [str(item) for item in chapter.get("body", []) if str(item).strip()]
    frame = chapter.get("frame") if isinstance(chapter.get("frame"), dict) else {}
    source_lines = [line for line in body if line.startswith(("步骤：", "步骤:", "操作：", "操作:"))]
    if unit_type == "operation" and not source_lines and body:
        source_lines = [body[0]]
    evidence = []
    if frame.get("src") and frame.get("timestamp"):
        evidence.append({
            "timestamp": str(frame["timestamp"]),
            "frame_src": str(frame["src"]),
            "proves": str(chapter.get("visual_anchor") or chapter.get("title") or "视频画面证据"),
        })
    result: dict[str, Any] = {
        "chapter_id": f"chapter-{index}",
        "chapter_index": index,
        "title": str(chapter.get("title") or ""),
        "time_range": str(chapter.get("time_range") or ""),
        "unit_type": unit_type,
        "template_type": template if template in _TEMPLATE_TYPES else (
            "sop" if unit_type == "operation" else "brief" if unit_type == "brief" else "concept"
        ),
        "body": body,
        "visual_anchor": str(chapter.get("visual_anchor") or ""),
        "author_statement": "",
        "plain_rewrite": "",
        "ai_advice": {
            "verdict": "",
            "analysis": "",
            "guidance": [],
        },
        "citations": [],
        "teaching_supplements": [],
        "tips": [],
        "evidence": evidence,
        "diagram_type": "none",
        "detail_restoration": chapter.get("detail_restoration", []),
        "key_quote": chapter.get("key_quote", ""),
        "learning_question": "",
        "author_examples": [],
        "case_reconstruction": {
            "context": "",
            "sequence": [],
            "result": "",
        },
        "reader_explanation": "",
        "core_takeaway": "",
        "reusable_pattern": "",
        "direct_application": "",
        "boundary_note": {
            "start_reason": "",
            "end_reason": "",
        },
    }
    if unit_type == "operation":
        result.update({
            "goal": "",
            "use_when": "",
            "operation_environment": "原视频未明确展示，待人工确认",
            "prerequisites": [],
            "source_operations": [
                {"text": line, "source_kind": "video_source"} for line in source_lines
            ],
            "original_examples": [],
            "verification": [],
            "troubleshooting": [],
        })
    elif unit_type == "concept":
        result.update({
            "use_when": "",
            "decision_rules": [],
            "verification": [],
        })
    return result


def load_actionable_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActionableValidationError(f"无法读取 actionable JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ActionableValidationError("actionable 顶层必须是对象")
    return payload


def validate_actionable_payload(
    payload: dict[str, Any],
    require_frames: bool = False,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ActionableValidationError("actionable 顶层必须是对象")
    schema_version = payload.get("schema_version")
    if type(schema_version) is not int or schema_version != 3:
        raise ActionableValidationError("schema_version 必须为 3")

    topology = payload.get("content_topology")
    if not isinstance(topology, dict):
        raise ActionableValidationError("content_topology 必须是对象")
    topology_type = topology.get("type")
    if not isinstance(topology_type, str) or topology_type not in TOPOLOGY_TYPES:
        raise ActionableValidationError("content_topology.type 不合法")
    _require_text(topology, "reason", "content_topology")

    learning_design_version = payload.get("learning_design_version")
    if (
        learning_design_version is not None
        and learning_design_version not in SUPPORTED_LEARNING_DESIGN_VERSIONS
    ):
        raise ActionableValidationError(
            "learning_design_version 仅支持 "
            + "、".join(sorted(SUPPORTED_LEARNING_DESIGN_VERSIONS))
        )
    ai_advice_enabled = payload.get("ai_advice_enabled")
    if ai_advice_enabled is not None and type(ai_advice_enabled) is not bool:
        raise ActionableValidationError("ai_advice_enabled 必须为布尔值")
    note_mode = payload.get("note_mode")
    if note_mode is not None:
        if note_mode not in NOTE_MODES:
            raise ActionableValidationError(f"note_mode 仅支持 {sorted(NOTE_MODES)}")
        if note_mode == "source-faithful" and ai_advice_enabled:
            raise ActionableValidationError("source-faithful 模式必须关闭 AI 建议")

    learning_path = _require_list(payload, "learning_path", "顶层")
    chapters = _require_list(payload, "chapters", "顶层")
    sources = _require_list(payload, "sources", "顶层")
    chapter_limit = 40 if learning_design_version in SUPPORTED_LEARNING_DESIGN_VERSIONS else 12
    if len(chapters) > chapter_limit:
        raise ActionableValidationError(f"自然切章最多允许 {chapter_limit} 章")
    if "action_items" in payload:
        action_items = _require_list(payload, "action_items", "顶层")
        for item_index, item in enumerate(action_items):
            item_context = f"action_items[{item_index}]"
            if not isinstance(item, dict):
                raise ActionableValidationError(f"{item_context} 必须是对象")
            for field in ("who", "what", "when", "note"):
                _require_text(item, field, item_context)
    if "ai_summary" in payload:
        summary = payload["ai_summary"]
        if not isinstance(summary, dict):
            raise ActionableValidationError("ai_summary 必须是对象")
        for field in ("core_problem", "audience", "final_deliverable"):
            _require_text(summary, field, "ai_summary")
        _require_string_list(summary, "learning_outcomes", "ai_summary", nonempty=True)
    if topology_type in {"complete_course", "mixed_course"} and not learning_path:
        raise ActionableValidationError("完整或混合课程必须提供非空 learning_path")

    chapter_ids: set[str] = set()
    for index, chapter in enumerate(chapters):
        if not isinstance(chapter, dict):
            raise ActionableValidationError(f"chapters[{index}] 必须是对象")
        validate_actionable_chapter(
            chapter,
            index,
            require_frames,
            learning_design_version=learning_design_version,
            ai_advice_enabled=ai_advice_enabled,
        )
        chapter_id = chapter["chapter_id"]
        if chapter_id in chapter_ids:
            raise ActionableValidationError(f"chapter_id 重复: {chapter_id}")
        chapter_ids.add(chapter_id)

    stage_ids: set[str] = set()
    stage_dependencies: list[tuple[str, str, list[str]]] = []
    for index, stage in enumerate(learning_path):
        context = f"learning_path[{index}]"
        if not isinstance(stage, dict):
            raise ActionableValidationError(f"{context} 必须是对象")
        stage_id = _require_text(stage, "stage_id", context)
        if stage_id in stage_ids:
            raise ActionableValidationError(f"stage_id 重复: {stage_id}")
        stage_ids.add(stage_id)
        for field in ("title", "goal", "deliverable"):
            _require_text(stage, field, context)
        stage_chapter_ids = _require_string_list(stage, "chapter_ids", context)
        dependencies = _require_string_list(stage, "depends_on", context)
        stage_dependencies.append((context, stage_id, dependencies))
        for chapter_id in stage_chapter_ids:
            if chapter_id not in chapter_ids:
                raise ActionableValidationError(
                    f"{context}.chapter_ids 引用了不存在的章节: {chapter_id}"
                )

    for context, stage_id, dependencies in stage_dependencies:
        for dependency in dependencies:
            if dependency == stage_id:
                raise ActionableValidationError(f"{context}.depends_on 不能自依赖")
            if dependency not in stage_ids:
                raise ActionableValidationError(
                    f"{context}.depends_on 引用了不存在的阶段: {dependency}"
                )

    _validate_dependency_dag(stage_dependencies)

    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        context = f"sources[{index}]"
        if not isinstance(source, dict):
            raise ActionableValidationError(f"{context} 必须是对象")
        source_id = _require_text(source, "id", context)
        if source_id in source_ids:
            raise ActionableValidationError(f"source id 重复: {source_id}")
        source_ids.add(source_id)
        source_kind = source.get("kind")
        if not isinstance(source_kind, str) or source_kind not in SOURCE_KINDS:
            raise ActionableValidationError(f"{context}.kind 不合法")

    for index, chapter in enumerate(chapters):
        for citation in chapter["citations"]:
            if not isinstance(citation, str) or citation not in source_ids:
                raise ActionableValidationError(
                    f"chapters[{index}].citations 无法解析: {citation!r}"
                )

    return {
        "status": "ok",
        "chapter_count": len(chapters),
        "stage_count": len(learning_path),
        "learning_design_version": learning_design_version,
        "ai_advice_enabled": ai_advice_enabled,
        "note_mode": note_mode,
    }


def validate_actionable_chapter(
    chapter: dict[str, Any],
    index: int,
    require_frame: bool = False,
    learning_design_version: str | None = None,
    ai_advice_enabled: bool | None = None,
) -> None:
    context = f"chapters[{index}]"
    if not isinstance(chapter, dict):
        raise ActionableValidationError(f"{context} 必须是对象")

    for field in ("chapter_id", "title", "time_range", "visual_anchor"):
        _require_text(chapter, field, context)
    chapter_index = chapter.get("chapter_index")
    if (
        not isinstance(chapter_index, int)
        or isinstance(chapter_index, bool)
        or chapter_index <= 0
    ):
        raise ActionableValidationError(f"{context}.chapter_index 必须是正整数")
    _require_string_list(chapter, "body", context, nonempty=True)

    unit_type = chapter.get("unit_type")
    if not isinstance(unit_type, str) or unit_type not in _UNIT_TYPES:
        raise ActionableValidationError(f"{context}.unit_type 不合法")
    is_adaptive = learning_design_version == LEARNING_DESIGN_VERSION
    template_type = chapter.get("template_type")
    if template_type is not None:
        if not isinstance(template_type, str) or template_type not in _TEMPLATE_TYPES:
            raise ActionableValidationError(f"{context}.template_type 不合法")
        if not is_adaptive and template_type == "brief" and (
            chapter.get("diagram_spec") or str(chapter.get("svg") or "").strip()
        ):
            raise ActionableValidationError(f"{context}.brief 模板不能包含图表")
        if not is_adaptive and template_type == "matrix":
            matrix_rows = _require_nonempty_list(chapter, "decision_matrix", context)
            for row_index, row in enumerate(matrix_rows):
                row_context = f"{context}.decision_matrix[{row_index}]"
                if not isinstance(row, dict):
                    raise ActionableValidationError(f"{row_context} 必须是对象")
                for field in ("option", "avoid", "recommend"):
                    _require_text(row, field, row_context)
        if not is_adaptive and template_type == "concept" and "feynman_scaffolding" in chapter:
            scaffold = chapter["feynman_scaffolding"]
            if not isinstance(scaffold, dict):
                raise ActionableValidationError(f"{context}.feynman_scaffolding 必须是对象")
            for field in ("term", "definition", "metaphor", "misconception"):
                _require_text(scaffold, field, f"{context}.feynman_scaffolding")
    if "diagram_spec" in chapter:
        _validate_diagram_spec(chapter["diagram_spec"], f"{context}.diagram_spec")
    _require_string_list(chapter, "citations", context)
    if "chapter_summary" in chapter:
        _require_text(chapter, "chapter_summary", context)
    if "key_points" in chapter:
        _require_string_list(chapter, "key_points", context, nonempty=True)
    if "author_examples" in chapter:
        examples = _require_nonempty_list(chapter, "author_examples", context)
        for item_index, item in enumerate(examples):
            item_context = f"{context}.author_examples[{item_index}]"
            if not isinstance(item, dict):
                raise ActionableValidationError(f"{item_context} 必须是对象")
            for field in ("label", "text", "timestamp", "completeness"):
                _require_text(item, field, item_context)

    if learning_design_version == LEARNING_DESIGN_VERSION:
        _validate_adaptive_learning_chapter(
            chapter,
            context,
            require_frame,
            ai_advice_enabled=ai_advice_enabled,
        )
    elif learning_design_version == LEGACY_LEARNING_DESIGN_VERSION:
        _validate_learning_design_chapter(chapter, context, require_frame)

    if not is_adaptive and unit_type == "operation":
        for field in ("goal", "use_when"):
            _require_text(chapter, field, context)
        if "operation_environment" in chapter:
            _require_text(chapter, "operation_environment", context)
        _require_string_list(chapter, "prerequisites", context, nonempty=True)
        source_operations = _require_nonempty_list(chapter, "source_operations", context)
        for item_index, operation in enumerate(source_operations):
            item_context = f"{context}.source_operations[{item_index}]"
            if not isinstance(operation, dict):
                raise ActionableValidationError(f"{item_context} 必须是对象")
            _require_text(operation, "text", item_context)
            if operation.get("source_kind") != "video_source":
                raise ActionableValidationError(
                    f"{item_context}.source_kind 必须为 video_source"
                )
            for field in ("location", "action", "parameter_or_result"):
                if field in operation:
                    _require_text(operation, field, item_context)

    if not is_adaptive and unit_type == "concept":
        _require_text(chapter, "use_when", context)
        _require_string_list(chapter, "decision_rules", context, nonempty=True)

    if (
        not is_adaptive
        and
        unit_type in {"operation", "concept"}
        and learning_design_version != LEGACY_LEARNING_DESIGN_VERSION
    ):
        _require_string_list(chapter, "verification", context, nonempty=True)

    if not is_adaptive and unit_type == "operation":
        _validate_evidence(chapter, context, require_frame, nonempty=True)
    elif not is_adaptive and unit_type == "concept" and "evidence" in chapter:
        _validate_evidence(chapter, context, require_frame, nonempty=False)

    if "troubleshooting" in chapter and not isinstance(chapter["troubleshooting"], list):
        raise ActionableValidationError(f"{context}.troubleshooting 必须是列表")

    if "teaching_supplements" in chapter:
        supplements = _require_list(chapter, "teaching_supplements", context)
        for item_index, item in enumerate(supplements):
            item_context = f"{context}.teaching_supplements[{item_index}]"
            if not isinstance(item, dict):
                raise ActionableValidationError(f"{item_context} 必须是对象")
            source_kind = item.get("source_kind")
            if not isinstance(source_kind, str) or source_kind not in _SUPPLEMENT_KINDS:
                raise ActionableValidationError(f"{item_context}.source_kind 不合法")

    if "transfer_exercises" in chapter:
        exercises = _require_list(chapter, "transfer_exercises", context)
        for item_index, item in enumerate(exercises):
            item_context = f"{context}.transfer_exercises[{item_index}]"
            if not isinstance(item, dict):
                raise ActionableValidationError(f"{item_context} 必须是对象")
            _require_text(item, "example", item_context)
            disclosure = _require_text(item, "disclosure", item_context)
            if "非作者" not in disclosure:
                raise ActionableValidationError(
                    f"{item_context}.disclosure 必须明确说明非作者原演示"
                )
            if item.get("source_kind") != "transfer_exercise":
                raise ActionableValidationError(
                    f"{item_context}.source_kind 必须为 transfer_exercise"
                )


def _validate_adaptive_learning_chapter(
    chapter: dict[str, Any],
    context: str,
    require_frame: bool,
    ai_advice_enabled: bool | None,
) -> None:
    """校验按章节语义选择内容块的自适应学习结构。"""
    role = chapter.get("chapter_role")
    if not isinstance(role, str) or role not in _ADAPTIVE_CHAPTER_ROLES:
        raise ActionableValidationError(f"{context}.chapter_role 不合法")
    _require_text(chapter, "chapter_summary", context)

    if ai_advice_enabled is not None:
        author_statement = _require_text(chapter, "author_statement", context)
        _validate_single_sentence(author_statement, f"{context}.author_statement")
        _require_text(chapter, "plain_rewrite", context)
        advice = chapter.get("ai_advice")
        if ai_advice_enabled:
            if not isinstance(advice, dict):
                raise ActionableValidationError(f"{context}.ai_advice 必须是对象")
            verdict = advice.get("verdict")
            if not isinstance(verdict, str) or verdict not in _AI_ADVICE_VERDICTS:
                raise ActionableValidationError(f"{context}.ai_advice.verdict 不合法")
            _require_text(advice, "analysis", f"{context}.ai_advice")
            _require_string_list(
                advice,
                "guidance",
                f"{context}.ai_advice",
                nonempty=True,
            )
        elif advice is not None:
            raise ActionableValidationError(
                f"{context}.ai_advice 在 AI 建议关闭时必须省略"
            )

    quotes = _require_nonempty_list(chapter, "source_quotes", context)
    for item_index, item in enumerate(quotes):
        item_context = f"{context}.source_quotes[{item_index}]"
        if not isinstance(item, dict):
            raise ActionableValidationError(f"{item_context} 必须是对象")
        for field in ("text", "timestamp"):
            _require_text(item, field, item_context)

    blocks = _require_nonempty_list(chapter, "content_blocks", context)
    for block_index, block in enumerate(blocks):
        block_context = f"{context}.content_blocks[{block_index}]"
        if not isinstance(block, dict):
            raise ActionableValidationError(f"{block_context} 必须是对象")
        block_type = block.get("type")
        if not isinstance(block_type, str) or block_type not in _ADAPTIVE_BLOCK_TYPES:
            raise ActionableValidationError(f"{block_context}.type 不合法")
        _require_text(block, "title", block_context)

        if block_type in {"scope_facts", "limitations"}:
            _require_string_list(block, "items", block_context, nonempty=True)
        elif block_type in {"explanation", "summary", "application"}:
            _require_text(block, "text", block_context)
        elif block_type == "takeaway":
            _require_text(block, "text", block_context)
            if "pattern" in block:
                _require_text(block, "pattern", block_context)
        elif block_type == "case_reconstruction":
            _require_text(block, "context", block_context)
            _require_string_list(block, "sequence", block_context, nonempty=True)
            _require_text(block, "result", block_context)
        elif block_type == "process":
            _require_string_list(block, "steps", block_context, nonempty=True)
        elif block_type == "observation":
            _require_string_list(block, "common_focus", block_context, nonempty=True)
            _require_string_list(block, "author_resolution", block_context, nonempty=True)
        elif block_type == "comparison":
            rows = _require_nonempty_list(block, "rows", block_context)
            for row_index, row in enumerate(rows):
                row_context = f"{block_context}.rows[{row_index}]"
                if not isinstance(row, dict):
                    raise ActionableValidationError(f"{row_context} 必须是对象")
                if not any(
                    isinstance(row.get(field), str) and row[field].strip()
                    for field in ("label", "option")
                ):
                    raise ActionableValidationError(
                        f"{row_context} 必须提供 label 或 option"
                    )
                if not any(
                    isinstance(row.get(field), str) and row[field].strip()
                    for field in ("detail", "avoid", "recommend")
                ):
                    raise ActionableValidationError(
                        f"{row_context} 必须提供 detail、avoid 或 recommend"
                    )

    _validate_evidence(chapter, context, require_frame, nonempty=True)


def _validate_single_sentence(value: str, context: str) -> None:
    """确保页面中的作者原话只保留一句完整表达。"""
    sentence_endings = re.findall(r"[。！？!?]+", value.strip())
    if len(sentence_endings) > 1 or "\n" in value or "\r" in value:
        raise ActionableValidationError(f"{context} 必须只包含一句话")


def _validate_learning_design_chapter(
    chapter: dict[str, Any],
    context: str,
    require_frame: bool,
) -> None:
    """校验 B 统一骨架和按需启用的 C 静态观察模块。"""
    for field in (
        "learning_question",
        "reader_explanation",
        "core_takeaway",
        "reusable_pattern",
        "direct_application",
    ):
        _require_text(chapter, field, context)

    examples = _require_nonempty_list(chapter, "author_examples", context)
    for item_index, item in enumerate(examples):
        item_context = f"{context}.author_examples[{item_index}]"
        if not isinstance(item, dict):
            raise ActionableValidationError(f"{item_context} 必须是对象")
        for field in ("label", "text", "timestamp", "completeness"):
            _require_text(item, field, item_context)

    reconstruction = chapter.get("case_reconstruction")
    if not isinstance(reconstruction, dict):
        raise ActionableValidationError(f"{context}.case_reconstruction 必须是对象")
    _require_text(reconstruction, "context", f"{context}.case_reconstruction")
    _require_string_list(
        reconstruction,
        "sequence",
        f"{context}.case_reconstruction",
        nonempty=True,
    )
    _require_text(reconstruction, "result", f"{context}.case_reconstruction")

    boundary_note = chapter.get("boundary_note")
    if isinstance(boundary_note, dict):
        for field in ("start_reason", "end_reason"):
            _require_text(boundary_note, field, f"{context}.boundary_note")
    elif not isinstance(boundary_note, str) or not boundary_note.strip():
        raise ActionableValidationError(
            f"{context}.boundary_note 必须是非空字符串或对象"
        )

    if "evidence" in chapter:
        _validate_evidence(chapter, context, require_frame, nonempty=False)

    observation = chapter.get("observation")
    if observation is None:
        return
    if not isinstance(observation, dict):
        raise ActionableValidationError(f"{context}.observation 必须是对象")
    if observation.get("enabled") is not True:
        raise ActionableValidationError(
            f"{context}.observation.enabled 必须为 true；不启用时应省略 observation"
        )
    _require_string_list(
        observation,
        "common_focus",
        f"{context}.observation",
        nonempty=True,
    )
    _require_string_list(
        observation,
        "author_resolution",
        f"{context}.observation",
        nonempty=True,
    )


def _validate_diagram_spec(spec: Any, context: str) -> None:
    if not isinstance(spec, dict):
        raise ActionableValidationError(f"{context} 必须是对象")
    diagram_type = spec.get("type")
    if not isinstance(diagram_type, str) or diagram_type not in _DIAGRAM_TYPES:
        raise ActionableValidationError(f"{context}.type 不合法")
    if diagram_type == "none":
        return
    if diagram_type == "flow":
        _require_string_list(spec, "nodes", context, nonempty=True)
        links = _require_list(spec, "links", context)
        for index, link in enumerate(links):
            if not isinstance(link, list) or len(link) != 2 or any(
                not isinstance(item, str) or not item.strip() for item in link
            ):
                raise ActionableValidationError(f"{context}.links[{index}] 必须包含两个节点名称")
    elif diagram_type == "radial":
        _require_text(spec, "center", context)
        _require_string_list(spec, "branches", context, nonempty=True)
    elif diagram_type == "matrix":
        _require_text(spec, "x_label", context)
        _require_text(spec, "y_label", context)
        points = _require_nonempty_list(spec, "points", context)
        for index, point in enumerate(points):
            point_context = f"{context}.points[{index}]"
            if not isinstance(point, dict):
                raise ActionableValidationError(f"{point_context} 必须是对象")
            _require_text(point, "label", point_context)
            for field in ("x", "y"):
                value = point.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 100:
                    raise ActionableValidationError(f"{point_context}.{field} 必须在 0 到 100 之间")


def _require_text(value: dict[str, Any], field: str, context: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise ActionableValidationError(f"{context}.{field} 必须是非空字符串")
    return item


def _require_list(value: dict[str, Any], field: str, context: str) -> list[Any]:
    item = value.get(field)
    if not isinstance(item, list):
        raise ActionableValidationError(f"{context}.{field} 必须是列表")
    return item


def _require_nonempty_list(
    value: dict[str, Any],
    field: str,
    context: str,
) -> list[Any]:
    item = _require_list(value, field, context)
    if not item:
        raise ActionableValidationError(f"{context}.{field} 必须是非空列表")
    return item


def _require_string_list(
    value: dict[str, Any],
    field: str,
    context: str,
    nonempty: bool = False,
) -> list[str]:
    items = _require_list(value, field, context)
    if nonempty and not items:
        raise ActionableValidationError(f"{context}.{field} 必须是非空列表")
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ActionableValidationError(f"{context}.{field} 必须是非空字符串列表")
    return items


def _validate_evidence(
    chapter: dict[str, Any],
    context: str,
    require_frame: bool,
    nonempty: bool,
) -> None:
    evidence = _require_list(chapter, "evidence", context)
    if nonempty and not evidence:
        raise ActionableValidationError(f"{context}.evidence 必须是非空列表")
    for item_index, item in enumerate(evidence):
        item_context = f"{context}.evidence[{item_index}]"
        if not isinstance(item, dict):
            raise ActionableValidationError(f"{item_context} 必须是对象")
        for field in ("timestamp", "frame_src", "proves"):
            _require_text(item, field, item_context)
        if require_frame and not _is_safe_relative_path(item["frame_src"]):
            raise ActionableValidationError(
                f"{item_context}.frame_src 必须是安全相对路径"
            )


def _is_safe_relative_path(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    if urlsplit(value).scheme:
        return False
    windows_path = PureWindowsPath(value)
    posix_path = PurePosixPath(value)
    if windows_path.is_absolute() or posix_path.is_absolute():
        return False
    if windows_path.drive or windows_path.root or posix_path.root:
        return False
    return ".." not in windows_path.parts and ".." not in posix_path.parts


def _validate_dependency_dag(
    stage_dependencies: list[tuple[str, str, list[str]]],
) -> None:
    indegrees = {
        stage_id: len(dependencies)
        for _, stage_id, dependencies in stage_dependencies
    }
    dependents = {stage_id: [] for stage_id in indegrees}
    for _, stage_id, dependencies in stage_dependencies:
        for dependency in dependencies:
            dependents[dependency].append(stage_id)

    ready = [stage_id for stage_id, degree in indegrees.items() if degree == 0]
    processed = 0
    next_ready = 0
    while next_ready < len(ready):
        stage_id = ready[next_ready]
        next_ready += 1
        processed += 1
        for dependent in dependents[stage_id]:
            indegrees[dependent] -= 1
            if indegrees[dependent] == 0:
                ready.append(dependent)

    if processed != len(indegrees):
        raise ActionableValidationError("learning_path dependency cycle detected")
