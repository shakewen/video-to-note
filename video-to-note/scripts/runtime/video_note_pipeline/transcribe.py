from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def _segment_value(segment: Any, field: str, default: Any = None) -> Any:
    if isinstance(segment, dict):
        return segment.get(field, default)
    return getattr(segment, field, default)


def _normalize_segments(segments: Iterable[Any]) -> list[dict[str, Any]]:
    normalized = []
    for index, segment in enumerate(segments):
        text = str(_segment_value(segment, "text", "")).strip()
        if not text:
            continue
        start = float(_segment_value(segment, "start", 0.0))
        end = float(_segment_value(segment, "end", start))
        normalized.append(
            {
                "id": index,
                "start": start,
                "end": max(start, end),
                "text": text,
            }
        )
    return normalized


def _srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _markdown_timestamp(seconds: float) -> str:
    return _srt_timestamp(seconds).replace(",", ".")


def write_transcript_outputs(
    audio_path: Path,
    output_dir: Path,
    language: str,
    segments: Iterable[Any],
) -> dict[str, Path]:
    normalized = _normalize_segments(segments)
    if not normalized:
        raise ValueError("转写结果没有可用片段")

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = audio_path.stem
    json_path = output_dir / f"{stem}.json"
    srt_path = output_dir / f"{stem}.srt"
    txt_path = output_dir / f"{stem}.txt"
    markdown_path = output_dir / "full-transcript.md"

    payload = {
        "text": " ".join(item["text"] for item in normalized),
        "language": language,
        "segments": normalized,
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    txt_path.write_text(
        "".join(f'{item["text"]}\n' for item in normalized),
        encoding="utf-8",
    )
    srt_blocks = []
    for index, item in enumerate(normalized, 1):
        srt_blocks.append(
            f"{index}\n"
            f'{_srt_timestamp(item["start"])} --> {_srt_timestamp(item["end"])}\n'
            f'{item["text"]}\n'
        )
    srt_path.write_text("\n".join(srt_blocks), encoding="utf-8")
    markdown_blocks = [
        "# 完整转写",
        "",
        "> 原始转写记录：按时间顺序保留每个有效 Whisper 分段；未经 AI 改写。",
    ]
    for item in normalized:
        markdown_blocks.extend(
            [
                "",
                f'## {_markdown_timestamp(item["start"])} → {_markdown_timestamp(item["end"])}',
                "",
                item["text"],
            ]
        )
    markdown_path.write_text("\n".join(markdown_blocks) + "\n", encoding="utf-8")
    return {"json": json_path, "srt": srt_path, "txt": txt_path, "markdown": markdown_path}


def transcribe_with_faster_whisper(
    audio_path: Path,
    output_dir: Path,
    model_name: str,
    language: str,
    model_dir: Path,
) -> dict[str, Path]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "当前 Python 缺少 faster_whisper；请改用已安装该模块的 Python，"
            "不要自动重复安装。"
        ) from exc

    model_dir.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(
        model_name,
        device="cpu",
        compute_type="int8",
        download_root=str(model_dir),
    )
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        task="transcribe",
        vad_filter=True,
    )
    detected_language = str(getattr(info, "language", None) or language)
    return write_transcript_outputs(
        audio_path,
        output_dir,
        detected_language,
        segments,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="使用 faster-whisper 生成兼容 video-to-note 的转写文件。"
    )
    parser.add_argument("audio_path", type=Path)
    parser.add_argument("--backend", choices=("faster-whisper",), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--language", choices=("zh", "en"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.audio_path.is_file():
        raise FileNotFoundError(f"音频文件不存在：{args.audio_path}")
    outputs = transcribe_with_faster_whisper(
        args.audio_path,
        args.output_dir,
        args.model,
        args.language,
        args.model_dir,
    )
    print(
        json.dumps(
            {name: str(path) for name, path in outputs.items()},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
