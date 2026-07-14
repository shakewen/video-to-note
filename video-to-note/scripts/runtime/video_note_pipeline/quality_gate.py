from pathlib import Path
from typing import Any

from .assessment import assess_quality
from .report import render_quality_report


def quality_action(result: dict[str, Any]) -> str:
    if result["duration_status"] != "ok":
        return "redownload_or_mark_abnormal"
    if result["transcript_status"] != "transcript_ok":
        return "review_transcript_or_mark_abnormal"
    return "continue"


def render_quality_gate_report(video_id: str, result: dict[str, Any]) -> str:
    action = quality_action(result)
    abnormal_notes = []
    if result["duration_status"] != "ok":
        abnormal_notes.append("Audio duration differs from metadata by more than tolerance.")
    if result["transcript_status"] != "transcript_ok":
        abnormal_notes.append("Last Whisper segment is not close to audio duration.")

    report = render_quality_report(
        video_id=video_id,
        metadata_duration=result["metadata_duration"],
        audio_duration=result["audio_duration"],
        duration_check_status=result["duration_status"],
        last_segment_end=result["last_segment_end"],
        transcript_check_status=result["transcript_status"],
        abnormal_notes=abnormal_notes,
    )
    return report + f"\n## Gate\n- action: {action}\n"


def write_quality_gate_report(
    video_id: str,
    metadata_json_path: Path,
    ffprobe_output_path: Path,
    transcript_json_path: Path,
    output_path: Path,
) -> str:
    result = assess_quality(metadata_json_path, ffprobe_output_path, transcript_json_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_quality_gate_report(video_id, result), encoding="utf-8")
    return quality_action(result)
