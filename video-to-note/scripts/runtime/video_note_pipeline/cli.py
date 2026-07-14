import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from .assessment import assess_quality
from .actionable import (
    ActionableValidationError,
    load_actionable_payload,
    prepare_actionable_skeleton,
    validate_actionable_payload,
)
from .chapters import ChapterValidationError, load_chapters_json, validate_chapters
from .commands import (
    build_audio_command,
    build_chrome_screenshot_command,
    build_crop_command,
    build_ffprobe_duration_command,
    build_frame_command,
    build_local_audio_command,
    build_metadata_command,
    build_video_command,
    build_whisper_command,
    format_command,
)
from .config import ConfigError, validate_config
from .cognitive import prepare_cognitive_chapters
from .delivery import render_delivery_report, verify_delivery
from .draft import write_draft_chapters
from .evidence import build_evidence_pack
from .frames import plan_candidate_frame_commands, plan_frame_commands
from .html import render_html
from .metadata import render_metadata_audit_report
from .note import render_note_html
from .paths import build_output_paths
from .quality_gate import write_quality_gate_report
from .render_check import PNGValidationError, inspect_png, plan_crop_slices
from .report import render_quality_report
from .runbook import render_manual_steps
from .source import SourceResolutionError, resolve_source, write_local_metadata
from .slices import plan_crop_command_report, write_slice_manifest
from .translation import write_finalized_translation, write_translation_draft


DEFAULT_TOOLS = ["yt-dlp", "ffmpeg", "ffprobe", "whisper", "chrome", "msedge"]

TOOL_HINTS = {
    "yt-dlp": {
        "install": "python -m pip install -U yt-dlp",
        "verify": "yt-dlp --version",
    },
    "ffmpeg": {
        "install": "winget install Gyan.FFmpeg",
        "verify": "ffmpeg -version",
    },
    "ffprobe": {
        "install": "winget install Gyan.FFmpeg",
        "verify": "ffprobe -version",
    },
    "whisper": {
        "install": "python -m pip install -U openai-whisper",
        "verify": "whisper --help",
    },
    "chrome": {
        "install": "winget install Google.Chrome",
        "verify": "chrome --version",
    },
    "msedge": {
        "install": "winget install Microsoft.Edge",
        "verify": "msedge --version",
    },
}


def tool_status(tools: list[str] | None = None) -> dict[str, dict[str, str | bool | None]]:
    selected_tools = tools or DEFAULT_TOOLS
    result = {}
    for tool in selected_tools:
        path = shutil.which(tool)
        result[tool] = {"available": path is not None, "path": path}
    return result


def doctor_report(status: dict[str, dict[str, str | bool | None]] | None = None) -> str:
    status = status or tool_status()
    missing = [tool for tool, item in status.items() if not item.get("available")]

    lines = [
        "# Tool Doctor",
        "",
        "| Tool | Status | Path | Install hint | Verify |",
        "| --- | --- | --- | --- | --- |",
    ]
    for tool, item in status.items():
        hints = TOOL_HINTS.get(tool, {})
        available = bool(item.get("available"))
        state = "available" if available else "missing"
        path = str(item.get("path") or "-")
        install = hints.get("install", "-") if not available else "-"
        verify = hints.get("verify", f"{tool} --version")
        lines.append(f"| {tool} | {state} | {path} | `{install}` | `{verify}` |")

    lines.extend(["", "## Next step"])
    if missing:
        lines.append(
            "Install the missing tools, restart PowerShell so PATH is refreshed, then run "
            "`./pipeline/run_pipeline.ps1 doctor` again."
        )
    else:
        lines.append("All required command-line tools are visible on PATH. Continue with `plan-commands`.")

    return "\n".join(lines) + "\n"


def plan_commands(config: dict[str, Any]) -> str:
    config = validate_config(config)
    video = config.get("video", {})
    cookies = config.get("cookies", {})
    language = config.get("language", {})
    output = config.get("output", {})

    url = video.get("url") or "<video-url>"
    video_id = video.get("expected_id") or "video"
    primary_language = language.get("primary", "zh")
    output_root = Path(output.get("root_dir", "./outputs"))
    paths = build_output_paths(output_root, video_id)

    is_local = video.get("source_kind") == "local_file" or video.get("platform") == "local"
    if is_local:
        metadata_cmd = [
            ".\\pipeline\\run_pipeline.ps1",
            "write-local-metadata",
            url,
            str(paths.metadata / "metadata.full.json"),
            "--source-id",
            video_id.removeprefix("local_"),
        ]
        audio_cmd = build_local_audio_command(url, str(paths.media / "audio.mp3"))
        frame_video_path = url
    else:
        metadata_cmd = build_metadata_command(url, cookies, str(paths.metadata))
        audio_cmd = build_audio_command(url, cookies, str(paths.media))
        frame_video_path = str(paths.media / "video.mp4")
    metadata_audit_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "audit-metadata",
        str(paths.metadata / "metadata.full.json"),
    ]
    video_cmd = None if is_local else build_video_command(url, cookies, str(paths.media))
    ffprobe_cmd = build_ffprobe_duration_command(str(paths.media / "audio.mp3"))
    whisper_cmd = build_whisper_command(str(paths.media / "audio.mp3"), primary_language, str(paths.transcript))
    quality_transcript = paths.transcript / "<transcript>.json"
    translation_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "draft-translation",
        str(paths.transcript / "<transcript>.json"),
        str(paths.transcript / "translation.zh-draft.json"),
    ]
    finalize_translation_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "finalize-translation",
        str(paths.transcript / "translation.zh-draft.json"),
        str(paths.transcript / "transcript.zh.json"),
    ]
    chapter_source = paths.transcript / "<transcript>.json"
    if primary_language == "en":
        chapter_source = paths.transcript / "transcript.zh.json"
        quality_transcript = paths.transcript / "transcript.zh.json"
    quality_gate_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "quality-gate",
        video_id,
        str(paths.metadata / "metadata.full.json"),
        str(paths.metadata / "ffprobe_duration.txt"),
        str(quality_transcript),
        str(paths.root / "quality_report.md"),
    ]
    draft_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "draft-chapters",
        str(chapter_source),
        str(paths.root / "chapters.json"),
        "--include-frames",
    ]
    cognitive_prepare_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "prepare-cognitive-note",
        str(paths.root / "chapters.json"),
        str(paths.root / "chapters.cognitive.json"),
    ]
    evidence_pack_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "build-evidence-pack",
        str(paths.metadata / "metadata.full.json"),
        str(chapter_source),
        str(paths.root / "chapters.cognitive.json"),
        str(paths.root / "evidence" / "evidence_pack.json"),
    ]
    actionable_prepare_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "prepare-actionable-note",
        str(paths.root / "evidence" / "evidence_pack.json"),
        str(paths.root / "chapters.actionable.json"),
    ]
    actionable_validate_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "validate-actionable-note",
        str(paths.root / "chapters.actionable.json"),
        "--require-frames",
    ]
    frame_plan_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "plan-candidate-frames",
        str(paths.root / "chapters.json"),
        frame_video_path,
        str(paths.html),
        "--every-seconds",
        "30",
        "--max-per-chapter",
        "6",
    ]
    final_frame_plan_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "plan-frames",
        str(paths.root / "chapters.actionable.json"),
        frame_video_path,
        str(paths.html),
    ]
    render_note_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "render-note",
        str(paths.metadata / "metadata.full.json"),
        str(paths.root / "chapters.actionable.json"),
        str(paths.html / "index.html"),
        "--require-frames",
    ]
    screenshot_cmd = build_chrome_screenshot_command(
        "chrome",
        str(paths.html / "index.html"),
        str(paths.render_check / "fullpage.png"),
    )
    crop_plan_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "plan-crop-commands",
        str(paths.render_check / "fullpage.png"),
        str(paths.render_check),
        "--slice-height",
        "1800",
        "--overlap",
        "100",
    ]
    slice_manifest_cmd = [
        ".\\pipeline\\run_pipeline.ps1",
        "write-slice-manifest",
        str(paths.render_check / "fullpage.png"),
        str(paths.render_check / "slice_manifest.json"),
        "--slice-height",
        "1800",
        "--overlap",
        "100",
    ]

    lines = [
        f"# Command Plan: {video_id}",
        "",
        "## 1. Metadata",
        f"`{format_command(metadata_cmd)}`",
        "",
        "## 2. Metadata Completeness Audit",
        f"`{format_command(metadata_audit_cmd)}`",
        "",
        "## 3. Best Audio to MP3",
        f"`{format_command(audio_cmd)}`",
        "",
        "## 4. Video for Frame Extraction",
        f"`{url}`（直接使用本地原文件，不重复复制）" if is_local else f"`{format_command(video_cmd or [])}`",
        "",
        "## 5. ffprobe Duration Check",
        f"`{format_command(ffprobe_cmd)}`",
        f"Save stdout to `{paths.metadata / 'ffprobe_duration.txt'}`.",
        "",
        "## 6. Whisper Transcript",
        f"`{format_command(whisper_cmd)}`",
        "",
    ]
    if primary_language == "en":
        lines.extend(
            [
                "## 7. English to Chinese Translation Draft",
                f"`{format_command(translation_cmd)}`",
                "",
                "## 8. Finalize Chinese Transcript",
                f"`{format_command(finalize_translation_cmd)}`",
                "",
                "## 9. Quality Gate",
                f"`{format_command(quality_gate_cmd)}`",
                "",
            ]
        )
        next_step_number = 10
    else:
        lines.extend(
            [
                "## 7. Quality Gate",
                f"`{format_command(quality_gate_cmd)}`",
                "",
            ]
        )
        next_step_number = 8

    lines.extend(
        [
        f"## {next_step_number}. Draft Chapter JSON from Transcript",
        f"`{format_command(draft_cmd)}`",
        "",
        f"## {next_step_number + 1}. Candidate Frame Extraction for Review",
        f"`{format_command(frame_plan_cmd)}`",
        "",
        f"## {next_step_number + 2}. Prepare Dynamic Cognitive Templates",
        f"`{format_command(cognitive_prepare_cmd)}`",
        "",
        f"## {next_step_number + 3}. Build Author Evidence Pack",
        f"`{format_command(evidence_pack_cmd)}`",
        "",
        f"## {next_step_number + 4}. Prepare Actionable Note Skeleton",
        f"`{format_command(actionable_prepare_cmd)}`",
        "",
        "Use `pipeline/prompts/actionable_note_rewrite.md` to enrich the skeleton with researched, source-labelled teaching content.",
        "",
        f"## {next_step_number + 5}. Validate Actionable Note",
        f"`{format_command(actionable_validate_cmd)}`",
        "",
        f"## {next_step_number + 6}. Final Chapter Frame Extraction",
        f"`{format_command(final_frame_plan_cmd)}`",
        "",
        f"## {next_step_number + 7}. Offline HTML Render",
        f"`{format_command(render_note_cmd)}`",
        "",
        f"## {next_step_number + 8}. Chrome Headless Render Check",
        f"`{format_command(screenshot_cmd)}`",
        "",
        f"## {next_step_number + 9}. ffmpeg Crop Slices",
        f"`{format_command(crop_plan_cmd)}`",
        "",
        f"## {next_step_number + 10}. Slice Manifest for Delivery Verification",
        f"`{format_command(slice_manifest_cmd)}`",
        "",
        "Use about 100px overlap between crop slices and adjust y offsets to avoid cutting titles.",
        ]
    )
    return "\n".join(lines) + "\n"


def manual_steps_report(config: dict[str, Any]) -> str:
    return render_manual_steps(config)


def resolve_source_report(value: str, cwd: str | Path | None = None) -> dict[str, Any]:
    return resolve_source(value, cwd=cwd).to_dict()


def assess_quality_report(
    video_id: str,
    metadata_json_path: Path,
    ffprobe_output_path: Path,
    transcript_json_path: Path,
) -> str:
    result = assess_quality(metadata_json_path, ffprobe_output_path, transcript_json_path)
    abnormal_notes = []
    if result["duration_status"] != "ok":
        abnormal_notes.append("Audio duration differs from metadata by more than tolerance.")
    if result["transcript_status"] != "transcript_ok":
        abnormal_notes.append("Last Whisper segment is not close to audio duration.")

    return render_quality_report(
        video_id=video_id,
        metadata_duration=result["metadata_duration"],
        audio_duration=result["audio_duration"],
        duration_check_status=result["duration_status"],
        last_segment_end=result["last_segment_end"],
        transcript_check_status=result["transcript_status"],
        abnormal_notes=abnormal_notes,
    )


def quality_gate_file(
    video_id: str,
    metadata_json_path: Path,
    ffprobe_output_path: Path,
    transcript_json_path: Path,
    output_path: Path,
) -> str:
    return write_quality_gate_report(
        video_id,
        metadata_json_path,
        ffprobe_output_path,
        transcript_json_path,
        output_path,
    )


def audit_metadata_report(metadata_json_path: Path) -> str:
    metadata = json.loads(metadata_json_path.read_text(encoding="utf-8-sig"))
    return render_metadata_audit_report(metadata)


def validate_chapters_report(chapters_json_path: Path, require_frames: bool = False) -> str:
    chapters = load_chapters_json(chapters_json_path)
    result = validate_chapters(chapters, require_frames=require_frames)
    lines = [
        "# Chapter Validation",
        "",
        f"- chapter_status: {result['status']}",
        f"- chapter_count: {result['chapter_count']}",
        f"- require_frames: {require_frames}",
    ]
    return "\n".join(lines) + "\n"


def inspect_png_report(path: Path) -> str:
    return json.dumps(inspect_png(path), ensure_ascii=False, indent=2)


def plan_crops_report(total_height: int, viewport_width: int, slice_height: int = 1800, overlap: int = 100) -> str:
    return json.dumps(
        plan_crop_slices(total_height, viewport_width, slice_height=slice_height, overlap=overlap),
        ensure_ascii=False,
        indent=2,
    )


def plan_crop_commands_report(input_png: Path, output_dir: Path, slice_height: int = 1800, overlap: int = 100) -> str:
    return plan_crop_command_report(input_png, output_dir, slice_height=slice_height, overlap=overlap)


def write_slice_manifest_file(input_png: Path, output_json: Path, slice_height: int = 1800, overlap: int = 100) -> str:
    manifest = write_slice_manifest(input_png, output_json, slice_height=slice_height, overlap=overlap)
    return json.dumps(manifest, ensure_ascii=False, indent=2)


def plan_frames_report(chapters_json_path: Path, video_path: str, html_dir: Path) -> str:
    chapters = load_chapters_json(chapters_json_path)
    return plan_frame_commands(chapters, video_path, html_dir)


def plan_candidate_frames_report(
    chapters_json_path: Path,
    video_path: str,
    html_dir: Path,
    every_seconds: int = 30,
    max_per_chapter: int = 6,
) -> str:
    chapters = load_chapters_json(chapters_json_path)
    return plan_candidate_frame_commands(
        chapters,
        video_path,
        html_dir,
        every_seconds=every_seconds,
        max_per_chapter=max_per_chapter,
    )


def verify_delivery_report(root: Path, require_frames: bool = True) -> str:
    return render_delivery_report(verify_delivery(root, require_frames=require_frames))


def render_note_file(
    metadata_json_path: Path,
    chapters_json_path: Path,
    output_path: Path,
    require_frames: bool = False,
) -> None:
    html = render_note_html(
        metadata_json_path,
        chapters_json_path,
        require_frames=require_frames,
        output_html_path=output_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def prepare_cognitive_note_file(
    chapters_json_path: Path,
    output_path: Path,
    overrides_json_path: Path | None = None,
) -> None:
    chapters = load_chapters_json(chapters_json_path)
    overrides = None
    if overrides_json_path:
        raw = json.loads(overrides_json_path.read_text(encoding="utf-8-sig"))
        overrides = raw.get("templates", raw) if isinstance(raw, dict) else None
    prepared = prepare_cognitive_chapters(chapters, overrides=overrides)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"schema_version": 2, "chapters": prepared}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_evidence_pack_file(
    metadata_path: Path,
    transcript_path: Path,
    chapters_path: Path,
    output_path: Path,
) -> None:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    transcript = json.loads(transcript_path.read_text(encoding="utf-8-sig"))
    cognitive = json.loads(chapters_path.read_text(encoding="utf-8-sig"))
    pack = build_evidence_pack(metadata, transcript, cognitive)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare_actionable_note_file(evidence_path: Path, output_path: Path) -> None:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
    payload = prepare_actionable_skeleton(evidence)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_actionable_note_report(path: Path, require_frames: bool = False) -> str:
    result = validate_actionable_payload(load_actionable_payload(path), require_frames=require_frames)
    return "\n".join(
        [
            "# Actionable Note Validation",
            "",
            f"- status: {result['status']}",
            f"- chapter_count: {result['chapter_count']}",
            f"- stage_count: {result['stage_count']}",
        ]
    )


def draft_chapters_file(
    transcript_json_path: Path,
    output_path: Path,
    chapter_seconds: int = 300,
    max_gap_seconds: int = 45,
    include_frames: bool = False,
) -> None:
    write_draft_chapters(
        transcript_json_path,
        output_path,
        chapter_seconds=chapter_seconds,
        max_gap_seconds=max_gap_seconds,
        include_frames=include_frames,
    )


def translation_draft_file(transcript_json_path: Path, output_path: Path) -> None:
    write_translation_draft(transcript_json_path, output_path)


def translation_finalize_file(draft_json_path: Path, output_path: Path) -> None:
    write_finalized_translation(draft_json_path, output_path)


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current_section: str | None = None
    current_list_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current_section = line[:-1].strip()
            root[current_section] = {}
            current_list_key = None
            continue
        if current_section is None:
            continue

        stripped = line.strip()
        section = root[current_section]
        if stripped.startswith("- ") and current_list_key:
            section[current_list_key].append(_parse_scalar(stripped[2:].strip()))
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value == "":
                section[key] = []
                current_list_key = key
            else:
                section[key] = _parse_scalar(value)
                current_list_key = None

    return root


def _parse_scalar(value: str) -> Any:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return int(value)
    except ValueError:
        return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Video note pipeline helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check-tools")
    subparsers.add_parser("doctor")

    resolve_parser = subparsers.add_parser("resolve-source")
    resolve_parser.add_argument("input")
    resolve_parser.add_argument("--cwd")

    local_metadata_parser = subparsers.add_parser("write-local-metadata")
    local_metadata_parser.add_argument("source_path")
    local_metadata_parser.add_argument("output_json")
    local_metadata_parser.add_argument("--source-id", required=True)

    plan_parser = subparsers.add_parser("plan-commands")
    plan_parser.add_argument("config")

    manual_parser = subparsers.add_parser("manual-steps")
    manual_parser.add_argument("config")

    report_parser = subparsers.add_parser("write-report-stub")
    report_parser.add_argument("video_id")

    metadata_parser = subparsers.add_parser("audit-metadata")
    metadata_parser.add_argument("metadata_json")

    sample_parser = subparsers.add_parser("render-sample-html")
    sample_parser.add_argument("output")

    render_note_parser = subparsers.add_parser("render-note")
    render_note_parser.add_argument("metadata_json")
    render_note_parser.add_argument("chapters_json")
    render_note_parser.add_argument("output_html")
    render_note_parser.add_argument("--require-frames", action="store_true")

    cognitive_parser = subparsers.add_parser("prepare-cognitive-note")
    cognitive_parser.add_argument("chapters_json")
    cognitive_parser.add_argument("output_json")
    cognitive_parser.add_argument("--overrides-json")

    evidence_parser = subparsers.add_parser("build-evidence-pack")
    evidence_parser.add_argument("metadata_json")
    evidence_parser.add_argument("transcript_json")
    evidence_parser.add_argument("cognitive_json")
    evidence_parser.add_argument("output_json")

    actionable_parser = subparsers.add_parser("prepare-actionable-note")
    actionable_parser.add_argument("evidence_json")
    actionable_parser.add_argument("output_json")

    actionable_validate_parser = subparsers.add_parser("validate-actionable-note")
    actionable_validate_parser.add_argument("actionable_json")
    actionable_validate_parser.add_argument("--require-frames", action="store_true")

    draft_parser = subparsers.add_parser("draft-chapters")
    draft_parser.add_argument("transcript_json")
    draft_parser.add_argument("output_json")
    draft_parser.add_argument("--chapter-seconds", type=int, default=300)
    draft_parser.add_argument("--max-gap-seconds", type=int, default=45)
    draft_parser.add_argument("--include-frames", action="store_true")

    translation_parser = subparsers.add_parser("draft-translation")
    translation_parser.add_argument("transcript_json")
    translation_parser.add_argument("output_json")

    finalize_translation_parser = subparsers.add_parser("finalize-translation")
    finalize_translation_parser.add_argument("translation_json")
    finalize_translation_parser.add_argument("output_json")

    assess_parser = subparsers.add_parser("assess-quality")
    assess_parser.add_argument("video_id")
    assess_parser.add_argument("metadata_json")
    assess_parser.add_argument("ffprobe_output")
    assess_parser.add_argument("transcript_json")

    gate_parser = subparsers.add_parser("quality-gate")
    gate_parser.add_argument("video_id")
    gate_parser.add_argument("metadata_json")
    gate_parser.add_argument("ffprobe_output")
    gate_parser.add_argument("transcript_json")
    gate_parser.add_argument("output_report")

    chapters_parser = subparsers.add_parser("validate-chapters")
    chapters_parser.add_argument("chapters_json")
    chapters_parser.add_argument("--require-frames", action="store_true")

    inspect_parser = subparsers.add_parser("inspect-png")
    inspect_parser.add_argument("png")

    crop_parser = subparsers.add_parser("plan-crops")
    crop_parser.add_argument("total_height", type=int)
    crop_parser.add_argument("viewport_width", type=int)
    crop_parser.add_argument("--slice-height", type=int, default=1800)
    crop_parser.add_argument("--overlap", type=int, default=100)

    crop_commands_parser = subparsers.add_parser("plan-crop-commands")
    crop_commands_parser.add_argument("input_png")
    crop_commands_parser.add_argument("output_dir")
    crop_commands_parser.add_argument("--slice-height", type=int, default=1800)
    crop_commands_parser.add_argument("--overlap", type=int, default=100)

    slice_manifest_parser = subparsers.add_parser("write-slice-manifest")
    slice_manifest_parser.add_argument("input_png")
    slice_manifest_parser.add_argument("output_json")
    slice_manifest_parser.add_argument("--slice-height", type=int, default=1800)
    slice_manifest_parser.add_argument("--overlap", type=int, default=100)

    frames_parser = subparsers.add_parser("plan-frames")
    frames_parser.add_argument("chapters_json")
    frames_parser.add_argument("video_path")
    frames_parser.add_argument("html_dir")

    candidate_frames_parser = subparsers.add_parser("plan-candidate-frames")
    candidate_frames_parser.add_argument("chapters_json")
    candidate_frames_parser.add_argument("video_path")
    candidate_frames_parser.add_argument("html_dir")
    candidate_frames_parser.add_argument("--every-seconds", type=int, default=30)
    candidate_frames_parser.add_argument("--max-per-chapter", type=int, default=6)

    delivery_parser = subparsers.add_parser("verify-delivery")
    delivery_parser.add_argument("root")
    delivery_parser.add_argument("--no-require-frames", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "check-tools":
        print(json.dumps(tool_status(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "doctor":
        print(doctor_report())
        return 0
    if args.command == "resolve-source":
        try:
            print(json.dumps(resolve_source_report(args.input, args.cwd), ensure_ascii=False))
            return 0
        except SourceResolutionError as error:
            print(f"Source error: {error}", file=sys.stderr)
            return 2
    if args.command == "write-local-metadata":
        try:
            write_local_metadata(args.source_path, args.output_json, args.source_id)
            print(args.output_json)
            return 0
        except SourceResolutionError as error:
            print(f"Source error: {error}", file=sys.stderr)
            return 2
    if args.command == "plan-commands":
        try:
            print(plan_commands(load_config(Path(args.config))))
            return 0
        except ConfigError as error:
            print(f"Config error: {error}", file=sys.stderr)
            return 2
    if args.command == "manual-steps":
        try:
            print(manual_steps_report(load_config(Path(args.config))))
            return 0
        except ConfigError as error:
            print(f"Config error: {error}", file=sys.stderr)
            return 2
    if args.command == "write-report-stub":
        print(
            render_quality_report(
                video_id=args.video_id,
                metadata_duration=None,
                audio_duration=None,
                duration_check_status="not_run",
                last_segment_end=None,
                transcript_check_status="not_run",
                abnormal_notes=[],
            )
        )
        return 0
    if args.command == "audit-metadata":
        print(audit_metadata_report(Path(args.metadata_json)))
        return 0
    if args.command == "render-sample-html":
        html = render_html(
            title="视频笔记样例",
            metadata={"uploader": "示例 UP", "duration": "10:00"},
            chapters=[
                {
                    "title": "示例章节",
                    "time_range": "00:00-02:00",
                    "body": ["这里展示正文先行。", "SVG 用来说明关系，截图用来给出视频证据。"],
                    "quote": "关键引用会保留短句。",
                    "visual_anchor": "00:42 画面中出现关键界面。",
                    "svg": '<svg viewBox="0 0 360 120" role="img" aria-label="示例图解"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#256d85"/></marker></defs><rect x="20" y="38" width="90" height="42" rx="6" fill="#e7f2f4" stroke="#256d85"/><text x="42" y="64" font-size="14">正文</text><line x1="112" y1="59" x2="168" y2="59" stroke="#256d85" stroke-width="2" marker-end="url(#arrow)"/><rect x="170" y="38" width="90" height="42" rx="6" fill="#fff" stroke="#256d85"/><text x="196" y="64" font-size="14">图解</text><line x1="262" y1="59" x2="318" y2="59" stroke="#256d85" stroke-width="2" marker-end="url(#arrow)"/><text x="282" y="96" font-size="13" fill="#68635c">截图实证</text></svg>',
                    "frame": {"src": "./frames/sample_42s.jpg", "timestamp": "00:42"},
                }
            ],
        )
        Path(args.output).write_text(html, encoding="utf-8")
        return 0
    if args.command == "render-note":
        try:
            render_note_file(
                Path(args.metadata_json),
                Path(args.chapters_json),
                Path(args.output_html),
                require_frames=args.require_frames,
            )
            return 0
        except (ChapterValidationError, ActionableValidationError) as error:
            print(f"Chapter validation error: {error}", file=sys.stderr)
            return 2
    if args.command == "prepare-cognitive-note":
        try:
            prepare_cognitive_note_file(
                Path(args.chapters_json),
                Path(args.output_json),
                Path(args.overrides_json) if args.overrides_json else None,
            )
            return 0
        except (ChapterValidationError, ValueError, json.JSONDecodeError) as error:
            print(f"Cognitive preparation error: {error}", file=sys.stderr)
            return 2
    if args.command == "build-evidence-pack":
        try:
            build_evidence_pack_file(
                Path(args.metadata_json), Path(args.transcript_json),
                Path(args.cognitive_json), Path(args.output_json),
            )
            return 0
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"Evidence pack error: {error}", file=sys.stderr)
            return 2
    if args.command == "prepare-actionable-note":
        try:
            prepare_actionable_note_file(Path(args.evidence_json), Path(args.output_json))
            return 0
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"Actionable preparation error: {error}", file=sys.stderr)
            return 2
    if args.command == "validate-actionable-note":
        try:
            print(validate_actionable_note_report(Path(args.actionable_json), args.require_frames))
            return 0
        except ActionableValidationError as error:
            print(f"Actionable validation error: {error}", file=sys.stderr)
            return 2
    if args.command == "draft-chapters":
        try:
            draft_chapters_file(
                Path(args.transcript_json),
                Path(args.output_json),
                chapter_seconds=args.chapter_seconds,
                max_gap_seconds=args.max_gap_seconds,
                include_frames=args.include_frames,
            )
            return 0
        except ValueError as error:
            print(f"Draft error: {error}", file=sys.stderr)
            return 2
    if args.command == "draft-translation":
        try:
            translation_draft_file(Path(args.transcript_json), Path(args.output_json))
            return 0
        except ValueError as error:
            print(f"Translation draft error: {error}", file=sys.stderr)
            return 2
    if args.command == "finalize-translation":
        try:
            translation_finalize_file(Path(args.translation_json), Path(args.output_json))
            return 0
        except ValueError as error:
            print(f"Translation finalize error: {error}", file=sys.stderr)
            return 2
    if args.command == "assess-quality":
        print(
            assess_quality_report(
                args.video_id,
                Path(args.metadata_json),
                Path(args.ffprobe_output),
                Path(args.transcript_json),
            )
        )
        return 0
    if args.command == "quality-gate":
        action = quality_gate_file(
            args.video_id,
            Path(args.metadata_json),
            Path(args.ffprobe_output),
            Path(args.transcript_json),
            Path(args.output_report),
        )
        print(f"action: {action}")
        return 0
    if args.command == "validate-chapters":
        try:
            print(validate_chapters_report(Path(args.chapters_json), require_frames=args.require_frames))
            return 0
        except ChapterValidationError as error:
            print(f"Chapter validation error: {error}", file=sys.stderr)
            return 2
    if args.command == "inspect-png":
        try:
            print(inspect_png_report(Path(args.png)))
            return 0
        except PNGValidationError as error:
            print(f"PNG validation error: {error}", file=sys.stderr)
            return 2
    if args.command == "plan-crops":
        print(
            plan_crops_report(
                args.total_height,
                args.viewport_width,
                slice_height=args.slice_height,
                overlap=args.overlap,
            )
        )
        return 0
    if args.command == "plan-crop-commands":
        try:
            print(
                plan_crop_commands_report(
                    Path(args.input_png),
                    Path(args.output_dir),
                    slice_height=args.slice_height,
                    overlap=args.overlap,
                )
            )
            return 0
        except (PNGValidationError, ValueError) as error:
            print(f"Crop command planning error: {error}", file=sys.stderr)
            return 2
    if args.command == "write-slice-manifest":
        try:
            print(
                write_slice_manifest_file(
                    Path(args.input_png),
                    Path(args.output_json),
                    slice_height=args.slice_height,
                    overlap=args.overlap,
                )
            )
            return 0
        except (PNGValidationError, ValueError) as error:
            print(f"Slice manifest error: {error}", file=sys.stderr)
            return 2
    if args.command == "plan-frames":
        try:
            print(plan_frames_report(Path(args.chapters_json), args.video_path, Path(args.html_dir)))
            return 0
        except ChapterValidationError as error:
            print(f"Chapter validation error: {error}", file=sys.stderr)
            return 2
    if args.command == "plan-candidate-frames":
        try:
            print(
                plan_candidate_frames_report(
                    Path(args.chapters_json),
                    args.video_path,
                    Path(args.html_dir),
                    every_seconds=args.every_seconds,
                    max_per_chapter=args.max_per_chapter,
                )
            )
            return 0
        except ChapterValidationError as error:
            print(f"Chapter validation error: {error}", file=sys.stderr)
            return 2
    if args.command == "verify-delivery":
        print(verify_delivery_report(Path(args.root), require_frames=not args.no_require_frames))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
