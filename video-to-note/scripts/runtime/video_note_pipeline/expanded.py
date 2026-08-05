from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


EXPANDED_SCHEMA_VERSION = 1
UNIT_TYPES = {"concept", "method", "operation", "fact"}
VERIFICATION_STATUSES = {"verified", "unresolved", "not_checked"}
_UNIT_REQUIRED_FIELDS = {
    "concept": {"type", "title", "core", "plain"},
    "method": {"type", "title", "use_when", "decision_logic", "workflow"},
    "operation": {"type", "title", "goal", "steps", "checkpoints"},
    "fact": {"type", "title", "conclusion"},
}
_UNIT_OPTIONAL_FIELDS = {"example", "boundary", "pitfall", "comparison", "memory_cue"}


class ExpandedValidationError(ValueError):
    pass


def load_expanded_payload(path: Path) -> dict[str, Any]:
    """读取 AI 重塑草稿，不把损坏 JSON 交给后续步骤。"""
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExpandedValidationError(f"无法读取 ai-expanded 草稿: {exc}") from exc
    if not isinstance(payload, dict):
        raise ExpandedValidationError("ai-expanded 草稿顶层必须是对象")
    return payload


def prepare_expanded_skeleton(
    source_path: Path,
    instruction: str = "",
) -> dict[str, Any]:
    """为 AI 重塑阶段创建不含读者内容的内部骨架。"""
    source_text, digest = _read_source(source_path)
    if not source_text:
        raise ExpandedValidationError("source-faithful Markdown 不能为空")
    return {
        "schema_version": EXPANDED_SCHEMA_VERSION,
        "source": {
            "path": str(source_path),
            "sha256": digest,
        },
        "request": {"instruction": instruction.strip()},
        "title": "",
        "thesis": "",
        "units": [],
        "application": [],
        "audit": {"verification": []},
    }


def validate_expanded_payload(
    payload: dict[str, Any],
    source_path: Path,
) -> dict[str, Any]:
    """校验扩展草稿仍基于未变化的 source-faithful 输入。"""
    if not isinstance(payload, dict):
        raise ExpandedValidationError("expanded 顶层必须是对象")
    if payload.get("schema_version") != EXPANDED_SCHEMA_VERSION:
        raise ExpandedValidationError(f"schema_version 必须为 {EXPANDED_SCHEMA_VERSION}")
    source = payload.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("sha256"), str):
        raise ExpandedValidationError("source.sha256 必须存在")
    _, actual_digest = _read_source(source_path)
    if source["sha256"] != actual_digest:
        raise ExpandedValidationError("source-faithful 已变化，请重新准备 expanded 草稿")
    _require_text(payload, "title", "顶层")
    _require_text(payload, "thesis", "顶层")
    units = _require_list(payload, "units", "顶层")
    if not units:
        raise ExpandedValidationError("units 必须是非空列表")
    titles: set[str] = set()
    for index, unit in enumerate(units):
        context = f"units[{index}]"
        if not isinstance(unit, dict):
            raise ExpandedValidationError(f"{context} 必须是对象")
        title = _validate_unit(unit, context)
        normalized_title = title.casefold()
        if normalized_title in titles:
            raise ExpandedValidationError(f"{context}.title 重复: {title}")
        titles.add(normalized_title)
    application = _require_string_list(payload, "application", "顶层")
    if len(application) > 3:
        raise ExpandedValidationError("application 最多允许 3 项")
    audit = payload.get("audit")
    if not isinstance(audit, dict):
        raise ExpandedValidationError("audit 必须是对象")
    verification = _require_list(audit, "verification", "audit")
    for index, item in enumerate(verification):
        if not isinstance(item, dict):
            raise ExpandedValidationError(f"audit.verification[{index}] 必须是对象")
        _validate_verification(item, f"audit.verification[{index}]")
    return {"status": "ok", "unit_count": len(units)}


def _validate_unit(unit: dict[str, Any], context: str) -> str:
    unit_type = _require_text(unit, "type", context)
    if unit_type not in UNIT_TYPES:
        raise ExpandedValidationError(f"{context}.type 不合法")
    allowed_fields = _UNIT_REQUIRED_FIELDS[unit_type] | _UNIT_OPTIONAL_FIELDS
    unknown_fields = set(unit) - allowed_fields
    if unknown_fields:
        raise ExpandedValidationError(f"{context} 包含不支持字段: {sorted(unknown_fields)}")
    title = _require_text(unit, "title", context)
    if unit_type == "concept":
        _require_text(unit, "core", context)
        _require_text(unit, "plain", context)
    elif unit_type == "method":
        _require_text(unit, "use_when", context)
        _require_text(unit, "decision_logic", context)
        _require_string_list(unit, "workflow", context, nonempty=True)
    elif unit_type == "operation":
        _require_text(unit, "goal", context)
        _require_string_list(unit, "steps", context, nonempty=True)
        _require_string_list(unit, "checkpoints", context, nonempty=True)
    else:
        _require_text(unit, "conclusion", context)
    for field in _UNIT_OPTIONAL_FIELDS & set(unit):
        value = unit[field]
        if isinstance(value, str) and value.strip():
            continue
        if isinstance(value, list) and value and all(isinstance(item, str) and item.strip() for item in value):
            continue
        raise ExpandedValidationError(f"{context}.{field} 必须是非空文本或非空文本列表")
    return title


def _validate_verification(item: dict[str, Any], context: str) -> None:
    _require_text(item, "topic", context)
    if item.get("reason") not in {"auto", "targeted"}:
        raise ExpandedValidationError(f"{context}.reason 不合法")
    status = item.get("status")
    if status not in VERIFICATION_STATUSES:
        raise ExpandedValidationError(f"{context}.status 不合法")
    urls = _require_string_list(item, "reference_urls", context)
    if status == "verified" and not urls:
        raise ExpandedValidationError(f"{context}.verified 必须保留来源")


def _require_text(payload: dict[str, Any], field: str, context: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ExpandedValidationError(f"{context}.{field} 必须是非空文本")
    return value.strip()


def _require_list(payload: dict[str, Any], field: str, context: str) -> list[Any]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise ExpandedValidationError(f"{context}.{field} 必须是列表")
    return value


def _require_string_list(
    payload: dict[str, Any],
    field: str,
    context: str,
    nonempty: bool = False,
) -> list[str]:
    values = _require_list(payload, field, context)
    if nonempty and not values:
        raise ExpandedValidationError(f"{context}.{field} 必须是非空列表")
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ExpandedValidationError(f"{context}.{field} 必须只包含非空文本")
    return [value.strip() for value in values]


def write_expanded_markdown(
    payload: dict[str, Any],
    output_path: Path,
    source_path: Path,
) -> None:
    """写入不含内部证据与审计字段的独立学习 Markdown。"""
    validate_expanded_payload(payload, source_path)
    lines = [
        f"# {payload['title'].strip()}",
        "",
        "## 30 秒掌握",
        "",
        payload["thesis"].strip(),
        "",
    ]
    for unit in payload["units"]:
        lines.extend(_render_unit(unit))
    application = _require_string_list(payload, "application", "顶层")
    if application:
        lines.extend(["## 立即应用", ""])
        lines.extend(f"- {item}" for item in application)
        lines.append("")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    except OSError as exc:
        raise ExpandedValidationError(f"无法写入 ai-expanded Markdown: {exc}") from exc


def _render_unit(unit: dict[str, Any]) -> list[str]:
    lines = [f"## {unit['title'].strip()}", ""]
    unit_type = unit["type"]
    if unit_type == "concept":
        lines.extend([f"**一句话本质：** {unit['core'].strip()}", "", unit["plain"].strip(), ""])
    elif unit_type == "method":
        lines.extend([
            f"**什么时候用：** {unit['use_when'].strip()}",
            "",
            f"**判断逻辑：** {unit['decision_logic'].strip()}",
            "",
            "**最小流程：**",
            "",
        ])
        lines.extend(f"{index}. {step}" for index, step in enumerate(unit["workflow"], 1))
        lines.append("")
    elif unit_type == "operation":
        lines.extend([f"**目标：** {unit['goal'].strip()}", "", "**步骤：**", ""])
        lines.extend(f"{index}. {step}" for index, step in enumerate(unit["steps"], 1))
        lines.extend(["", "**检查点：**", ""])
        lines.extend(f"- {checkpoint}" for checkpoint in unit["checkpoints"])
        lines.append("")
    else:
        lines.extend([unit["conclusion"].strip(), ""])
    for field, label in (
        ("example", "例子"),
        ("boundary", "边界"),
        ("pitfall", "易错点"),
        ("comparison", "对比"),
        ("memory_cue", "记忆"),
    ):
        if field in unit:
            lines.extend(_render_optional_field(label, unit[field]))
    return lines


def _render_optional_field(label: str, value: Any) -> list[str]:
    if isinstance(value, str):
        return [f"**{label}：** {value.strip()}", ""]
    lines = [f"**{label}：**", ""]
    lines.extend(f"- {item.strip()}" for item in value)
    lines.append("")
    return lines


def _read_source(source_path: Path) -> tuple[str, str]:
    try:
        if not source_path.is_file():
            raise ExpandedValidationError("source-faithful Markdown 必须是文件")
        raw = source_path.read_bytes()
        text = raw.decode("utf-8-sig").strip()
    except (OSError, UnicodeError) as exc:
        raise ExpandedValidationError(f"无法读取 source-faithful Markdown: {exc}") from exc
    return text, sha256(raw).hexdigest()
