import json
from pathlib import Path
from typing import Any

from .quality import duration_delta_ratio, duration_status, transcript_tail_status


def extract_metadata_duration(metadata: dict[str, Any]) -> float:
    duration = metadata.get("duration")
    if duration is not None:
        return float(duration)

    entries = metadata.get("entries") or []
    total = 0.0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_duration = entry.get("duration")
        if entry_duration is not None:
            total += float(entry_duration)
    if total <= 0:
        raise ValueError("metadata duration is missing")
    return total


def parse_ffprobe_duration(output: str) -> float:
    stripped = output.strip().lstrip("\ufeff")
    if not stripped:
        raise ValueError("ffprobe duration output is empty")
    return float(stripped.splitlines()[-1])


def extract_transcript_last_end(transcript: dict[str, Any]) -> float:
    segments = transcript.get("segments") or []
    if not segments:
        raise ValueError("transcript has no segments")
    last = segments[-1]
    if not isinstance(last, dict) or last.get("end") is None:
        raise ValueError("last transcript segment has no end")
    return float(last["end"])


def assess_quality(
    metadata_json_path: Path,
    ffprobe_output_path: Path,
    transcript_json_path: Path,
    tolerance_percent: float = 5,
) -> dict[str, Any]:
    metadata = _read_json(metadata_json_path)
    transcript = _read_json(transcript_json_path)
    ffprobe_output = ffprobe_output_path.read_text(encoding="utf-8")

    metadata_duration = extract_metadata_duration(metadata)
    audio_duration = parse_ffprobe_duration(ffprobe_output)
    last_segment_end = extract_transcript_last_end(transcript)

    duration_check_status = duration_status(metadata_duration, audio_duration, tolerance_percent)
    transcript_check_status = transcript_tail_status(audio_duration, last_segment_end, tolerance_percent)

    return {
        "metadata_duration": metadata_duration,
        "audio_duration": audio_duration,
        "duration_delta_ratio": duration_delta_ratio(metadata_duration, audio_duration),
        "duration_status": duration_check_status,
        "last_segment_end": last_segment_end,
        "transcript_delta_ratio": abs(audio_duration - last_segment_end) / audio_duration,
        "transcript_status": transcript_check_status,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))
