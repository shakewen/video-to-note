from typing import Any


def summarize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": _first(metadata, "fulltitle", "title") or "视频笔记",
        "uploader": _first(metadata, "uploader", "channel", "creator"),
        "description": metadata.get("description"),
        "tags": metadata.get("tags") or [],
        "thumbnail": metadata.get("thumbnail"),
        "duration": metadata.get("duration"),
        "source_url": _first(metadata, "webpage_url", "original_url", "url"),
        "parts": _parts(metadata),
    }


def audit_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    checks = [
        ("title", _first(metadata, "fulltitle", "title")),
        ("uploader", _first(metadata, "uploader", "channel", "creator")),
        ("description", metadata.get("description")),
        ("tags", metadata.get("tags")),
        ("thumbnail", _thumbnail(metadata)),
        ("duration", metadata.get("duration")),
        ("source_url", _first(metadata, "webpage_url", "original_url", "url")),
    ]
    fields = []
    missing = []
    for name, value in checks:
        present = _is_present(value)
        fields.append({"name": name, "status": "present" if present else "missing", "value": value})
        if not present:
            missing.append(name)

    parts = _parts(metadata)
    warnings = []
    if parts:
        fields.append({"name": "parts", "status": "present", "value": parts})
    else:
        fields.append({"name": "parts", "status": "warning", "value": []})
        warnings.append("parts")

    status = "ok" if not missing and not warnings else "warning"
    return {"status": status, "fields": fields, "missing": missing, "warnings": warnings}


def render_metadata_audit_report(metadata: dict[str, Any]) -> str:
    result = audit_metadata(metadata)
    lines = [
        "# Metadata Audit",
        "",
        f"- status: {result['status']}",
        f"- missing: {', '.join(result['missing']) if result['missing'] else 'none'}",
        f"- warnings: {', '.join(result['warnings']) if result['warnings'] else 'none'}",
        "",
        "| Field | Status | Value |",
        "| --- | --- | --- |",
    ]
    for field in result["fields"]:
        value = field["value"]
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value[:5]) or "-"
        else:
            rendered = str(value) if value is not None else "-"
        lines.append(f"| {field['name']} | {field['status']} | {rendered} |")
    return "\n".join(lines) + "\n"


def _first(metadata: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = metadata.get(key)
        if value:
            return value
    return None


def _thumbnail(metadata: dict[str, Any]) -> Any:
    return metadata.get("thumbnail") or metadata.get("thumbnails") or metadata.get("thumbnail_url")


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _parts(metadata: dict[str, Any]) -> list[str]:
    entries = metadata.get("entries") or []
    parts = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        title = entry.get("title") or entry.get("fulltitle") or f"P{index}"
        parts.append(str(title))
    return parts
