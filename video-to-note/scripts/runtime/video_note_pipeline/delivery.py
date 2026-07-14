import json
from pathlib import Path, PurePosixPath
from typing import Any

from .actionable import ActionableValidationError, load_actionable_payload, validate_actionable_payload
from .chapters import ChapterValidationError, load_chapters_json, validate_chapters
from .render_check import PNGValidationError, inspect_png


def verify_delivery(root: Path, require_frames: bool = True) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    _check_file(checks, root, "metadata/metadata.full.json")
    _check_file(checks, root, "metadata/ffprobe_duration.txt")
    _check_glob(checks, root, "media/*.mp3", "media/*.mp3")
    _check_file(checks, root, "transcript/transcript.json")
    _check_glob(checks, root, "transcript/*.srt", "transcript/*.srt")
    _check_glob(checks, root, "transcript/*.txt", "transcript/*.txt")
    _check_chapters(checks, root, require_frames)
    _check_file(checks, root, "html/index.html")
    _check_html_chapter_content(checks, root, require_frames)
    if require_frames:
        _check_glob(checks, root, "html/frames/*", "html/frames/*")
        _check_chapter_frame_files(checks, root)
    _check_fullpage_png(checks, root)
    _check_glob(checks, root, "render-check/slice_*.png", "render-check/slice_*.png")
    _check_slice_manifest(checks, root)
    _check_quality_report(checks, root)

    failed_count = sum(1 for check in checks if check["status"] != "ok")
    return {
        "status": "ok" if failed_count == 0 else "incomplete",
        "root": str(root),
        "failed_count": failed_count,
        "checks": checks,
    }


def render_delivery_report(result: dict[str, Any]) -> str:
    lines = [
        "# Delivery Verification",
        "",
        f"- root: {result['root']}",
        f"- status: {result['status']}",
        f"- failed_count: {result['failed_count']}",
        "",
        "| status | item | detail |",
        "|---|---|---|",
    ]
    for check in result["checks"]:
        lines.append(f"| {check['status']} | {check['item']} | {check['detail']} |")
    return "\n".join(lines) + "\n"


def _check_file(checks: list[dict[str, str]], root: Path, relative_path: str) -> None:
    path = root / relative_path
    if path.is_file():
        checks.append({"status": "ok", "item": relative_path, "detail": "exists"})
    else:
        checks.append({"status": "missing", "item": relative_path, "detail": "file not found"})


def _check_glob(checks: list[dict[str, str]], root: Path, pattern: str, item: str) -> None:
    matches = sorted(root.glob(pattern))
    if matches:
        checks.append({"status": "ok", "item": item, "detail": f"{len(matches)} found"})
    else:
        checks.append({"status": "missing", "item": item, "detail": "no matches"})


def _check_chapters(checks: list[dict[str, str]], root: Path, require_frames: bool) -> None:
    path = _delivery_chapters_path(root)
    item_name = path.name
    if not path.is_file():
        checks.append({"status": "missing", "item": item_name, "detail": "file not found"})
        return
    try:
        if path.name == "chapters.actionable.json":
            result = validate_actionable_payload(load_actionable_payload(path), require_frames=require_frames)
        else:
            chapters = load_chapters_json(path)
            result = validate_chapters(chapters, require_frames=require_frames)
    except (ActionableValidationError, ChapterValidationError, ValueError) as error:
        checks.append({"status": "invalid", "item": item_name, "detail": str(error)})
        return
    checks.append({"status": "ok", "item": item_name, "detail": f"{result['chapter_count']} chapters"})


def _check_chapter_frame_files(checks: list[dict[str, str]], root: Path) -> None:
    path = _delivery_chapters_path(root)
    if not path.is_file():
        return
    try:
        payload = load_actionable_payload(path) if path.name == "chapters.actionable.json" else None
        chapters = payload["chapters"] if payload else load_chapters_json(path)
    except (ActionableValidationError, ChapterValidationError, ValueError):
        return

    html_root = (root / "html").resolve()
    for index, chapter in enumerate(chapters, start=1):
        if payload is not None:
            frames = [
                {"src": item.get("frame_src")}
                for item in chapter.get("evidence", [])
                if isinstance(item, dict) and item.get("frame_src")
            ]
        else:
            frame = chapter.get("frame") if isinstance(chapter, dict) else None
            frames = [frame] if isinstance(frame, dict) else []
        for frame in frames:
            src = str(frame.get("src", "")).strip()
            if not src:
                continue

            item = f"html/{src}"
            normalized = src.replace("\\", "/")
            while normalized.startswith("./"):
                normalized = normalized[2:]
            relative_path = PurePosixPath(normalized)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                checks.append({"status": "invalid", "item": item, "detail": f"chapter {index} frame path must stay inside html"})
                continue

            target = (html_root / Path(*relative_path.parts)).resolve()
            try:
                target.relative_to(html_root)
            except ValueError:
                checks.append({"status": "invalid", "item": item, "detail": f"chapter {index} frame path must stay inside html"})
                continue

            if target.is_file():
                checks.append({"status": "ok", "item": item, "detail": "referenced frame exists"})
            else:
                checks.append({"status": "missing", "item": item, "detail": f"chapter {index} referenced frame not found"})


def _check_html_chapter_content(checks: list[dict[str, str]], root: Path, require_frames: bool) -> None:
    html_path = root / "html" / "index.html"
    chapters_path = _delivery_chapters_path(root)
    if not html_path.is_file() or not chapters_path.is_file():
        return
    try:
        html = html_path.read_text(encoding="utf-8-sig")
        payload = load_actionable_payload(chapters_path) if chapters_path.name == "chapters.actionable.json" else None
        chapters = payload["chapters"] if payload else load_chapters_json(chapters_path)
    except (OSError, UnicodeDecodeError, ActionableValidationError, ChapterValidationError, ValueError) as error:
        checks.append({"status": "invalid", "item": "html/index.html", "detail": str(error)})
        return

    expected_chapter_count = len(chapters)
    expected_diagram_count = (
        sum(1 for chapter in chapters if chapter.get("svg"))
        if payload is not None
        else sum(1 for chapter in chapters if chapter.get("template_type") != "brief")
    )
    svg_count = html.count("<svg")
    if svg_count < expected_diagram_count:
        checks.append(
            {
                "status": "missing",
                "item": "html/index.html",
                "detail": f"chapter 1 svg missing or only {svg_count}/{expected_diagram_count} required SVGs found",
            }
        )
    else:
        checks.append(
            {
                "status": "ok",
                "item": "html/index.html",
                "detail": f"{svg_count} SVGs for {expected_diagram_count} diagram chapters ({expected_chapter_count} total)",
            }
        )

    if expected_diagram_count == 0:
        checks.append({"status": "ok", "item": "html/index.html", "detail": "no diagrams required by brief chapters"})
    elif "图解" in html:
        checks.append({"status": "ok", "item": "html/index.html", "detail": "diagram captions found"})
    else:
        checks.append({"status": "missing", "item": "html/index.html", "detail": "diagram caption 图解 missing"})

    for index, chapter in enumerate(chapters, start=1):
        title = str(chapter.get("title", "")).strip()
        if title and title in html:
            checks.append({"status": "ok", "item": f"html chapter {index}", "detail": f"title {title} found"})
        else:
            checks.append({"status": "missing", "item": f"html chapter {index}", "detail": "chapter title missing"})

        if not require_frames:
            continue
        if payload is not None:
            frame_sources = [str(item.get("frame_src", "")).strip() for item in chapter.get("evidence", []) if isinstance(item, dict)]
        else:
            frame = chapter.get("frame") if isinstance(chapter, dict) else None
            frame_sources = [str(frame.get("src", "")).strip()] if isinstance(frame, dict) else []
        if frame_sources and all(src and src in html for src in frame_sources):
            checks.append({"status": "ok", "item": f"html chapter {index} frames", "detail": "frame references found in HTML"})
        else:
            checks.append({"status": "missing", "item": f"html chapter {index} frames", "detail": f"chapter {index} frame reference missing in HTML"})

    if payload is not None:
        has_labelled_content = bool(payload.get("sources")) or any(chapter.get("teaching_supplements") or chapter.get("transfer_exercises") for chapter in chapters)
        if not has_labelled_content or "data-source-kind" in html:
            checks.append({"status": "ok", "item": "html/index.html", "detail": "source labels found"})
        else:
            checks.append({"status": "missing", "item": "html/index.html", "detail": "source labels missing"})
        if payload.get("learning_path") and 'class="learning-path"' not in html:
            checks.append({"status": "missing", "item": "html/index.html", "detail": "learning path missing"})
        else:
            checks.append({"status": "ok", "item": "html/index.html", "detail": "learning path found"})

    if require_frames:
        if "视频时间戳" in html:
            checks.append({"status": "ok", "item": "html/index.html", "detail": "frame captions found"})
        else:
            checks.append({"status": "missing", "item": "html/index.html", "detail": "frame caption 视频时间戳 missing"})


def _delivery_chapters_path(root: Path) -> Path:
    actionable = root / "chapters.actionable.json"
    if actionable.is_file():
        return actionable
    cognitive = root / "chapters.cognitive.json"
    if cognitive.is_file():
        return cognitive
    return root / "chapters.json"


def _check_fullpage_png(checks: list[dict[str, str]], root: Path) -> None:
    relative_path = "render-check/fullpage.png"
    path = root / relative_path
    if not path.is_file():
        checks.append({"status": "missing", "item": relative_path, "detail": "file not found"})
        return
    try:
        result = inspect_png(path)
    except PNGValidationError as error:
        checks.append({"status": "invalid", "item": relative_path, "detail": str(error)})
        return
    if result["is_blank"]:
        checks.append({"status": "invalid", "item": relative_path, "detail": "PNG appears blank"})
        return
    checks.append(
        {
            "status": "ok",
            "item": relative_path,
            "detail": f"{result['width']}x{result['height']}",
        }
    )


def _check_slice_manifest(checks: list[dict[str, str]], root: Path) -> None:
    relative_path = "render-check/slice_manifest.json"
    path = root / relative_path
    if not path.is_file():
        checks.append({"status": "missing", "item": relative_path, "detail": "file not found"})
        return
    try:
        manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        checks.append({"status": "invalid", "item": relative_path, "detail": str(error)})
        return

    slices = manifest.get("slices")
    if not isinstance(slices, list) or not slices:
        checks.append({"status": "invalid", "item": relative_path, "detail": "slices must be a non-empty list"})
        return

    fullpage_height = int(manifest.get("fullpage_height", 0) or 0)
    overlap = int(manifest.get("overlap", 0) or 0)
    fullpage_path = root / "render-check" / "fullpage.png"
    if fullpage_path.is_file():
        try:
            png_info = inspect_png(fullpage_path)
        except PNGValidationError as error:
            checks.append({"status": "invalid", "item": relative_path, "detail": str(error)})
            return
        if fullpage_height != int(png_info["height"]):
            checks.append(
                {
                    "status": "invalid",
                    "item": relative_path,
                    "detail": f"fullpage height {fullpage_height} does not match PNG {png_info['height']}",
                }
            )
            return

    if len(slices) > 1 and overlap < 100:
        checks.append({"status": "invalid", "item": relative_path, "detail": f"overlap {overlap}px is below 100px"})
        return

    previous_bottom: int | None = None
    for index, item in enumerate(slices, start=1):
        try:
            y = int(item["y"])
            height = int(item["height"])
            output = str(item["output"])
        except (KeyError, TypeError, ValueError):
            checks.append({"status": "invalid", "item": relative_path, "detail": f"slice {index} is incomplete"})
            return
        if index == 1 and y != 0:
            checks.append({"status": "invalid", "item": relative_path, "detail": "first slice must start at y=0"})
            return
        if previous_bottom is not None:
            actual_overlap = previous_bottom - y
            if actual_overlap < 0:
                checks.append({"status": "invalid", "item": relative_path, "detail": f"gap before slice {index}"})
                return
            if overlap >= 100 and actual_overlap < 100:
                checks.append(
                    {
                        "status": "invalid",
                        "item": relative_path,
                        "detail": f"slice {index} overlap {actual_overlap}px is below 100px",
                    }
                )
                return
        if not (root / "render-check" / output).is_file():
            checks.append(
                {
                    "status": "missing",
                    "item": f"render-check/{output}",
                    "detail": "slice listed in manifest not found",
                }
            )
            return
        previous_bottom = y + height

    if previous_bottom is None or previous_bottom < fullpage_height:
        checks.append({"status": "invalid", "item": relative_path, "detail": "slices do not cover full page"})
        return

    checks.append(
        {
            "status": "ok",
            "item": relative_path,
            "detail": f"{len(slices)} slices cover {fullpage_height}px with {overlap}px overlap",
        }
    )


def _check_quality_report(checks: list[dict[str, str]], root: Path) -> None:
    relative_path = "quality_report.md"
    path = root / relative_path
    if not path.is_file():
        checks.append({"status": "missing", "item": relative_path, "detail": "file not found"})
        return

    text = path.read_text(encoding="utf-8-sig")
    action = _extract_quality_action(text)
    if action != "continue":
        detail = f"action is {action or 'missing'}"
        checks.append({"status": "invalid", "item": relative_path, "detail": detail})
        return
    checks.append({"status": "ok", "item": relative_path, "detail": "action continue"})


def _extract_quality_action(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- action:"):
            return stripped.split(":", 1)[1].strip()
        if stripped.startswith("action:"):
            return stripped.split(":", 1)[1].strip()
    return None
