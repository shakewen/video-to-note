import json
from pathlib import Path
from typing import Any

from .draft import format_timestamp


def draft_translation_from_transcript(transcript_json_path: Path) -> dict[str, Any]:
    data = json.loads(transcript_json_path.read_text(encoding="utf-8-sig"))
    return draft_translation_from_segments(data.get("segments", []))


def draft_translation_from_segments(segments: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        items.append(
            {
                "start": start,
                "end": end,
                "timestamp": format_timestamp(start),
                "source_text": text,
                "zh_text": "",
                "needs_translation": True,
            }
        )

    if not items:
        raise ValueError("transcript segments are required")

    return {
        "source_language": "en",
        "target_language": "zh",
        "needs_translation": True,
        "instructions": [
            "Translate zh_text into concise Chinese notes, not word-for-word subtitles.",
            "Keep source_text unchanged for audit and short quotes.",
            "Preserve timestamps so chapters can link back to the video.",
        ],
        "segments": items,
    }


def write_translation_draft(transcript_json_path: Path, output_path: Path) -> None:
    draft = draft_translation_from_transcript(transcript_json_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")


def finalize_translation_to_transcript(draft: dict[str, Any]) -> dict[str, Any]:
    segments = []
    for index, segment in enumerate(draft.get("segments", []), start=1):
        text = str(segment.get("zh_text", "")).strip()
        if not text:
            raise ValueError(f"segment {index} is missing zh_text")
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        segments.append(
            {
                "start": start,
                "end": end,
                "text": text,
                "source_text": str(segment.get("source_text", "")).strip(),
            }
        )

    if not segments:
        raise ValueError("translated segments are required")

    return {"language": "zh", "source_language": "en", "segments": segments}


def write_finalized_translation(draft_json_path: Path, output_path: Path) -> None:
    draft = json.loads(draft_json_path.read_text(encoding="utf-8-sig"))
    transcript = finalize_translation_to_transcript(draft)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
