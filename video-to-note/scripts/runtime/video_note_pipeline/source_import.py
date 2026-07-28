from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .commands import build_video_downloader_command


def _require_file(value: Any, label: str) -> Path:
    path = Path(str(value or "")).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"video-downloader 未生成有效{label}：{path}")
    return path


def _normalized_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    author = raw.get("author") if isinstance(raw.get("author"), dict) else {}
    video = raw.get("video") if isinstance(raw.get("video"), dict) else {}
    source_url = raw.get("source_url") or raw.get("final_url")
    return {
        "title": raw.get("title"),
        "uploader": author.get("nickname") or author.get("id"),
        "description": raw.get("description"),
        "tags": raw.get("tags") or [],
        "duration": video.get("duration_seconds"),
        "webpage_url": source_url,
        "original_url": source_url,
    }


def import_downloader_result(result: dict[str, Any], output_root: Path) -> dict[str, str]:
    """将下载器结果整理为 video-to-note 的稳定目录结构。"""
    video_path = _require_file(result.get("video_path"), "视频文件")
    metadata_path = _require_file(result.get("metadata_path"), "元数据文件")
    raw_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(raw_metadata, dict):
        raise ValueError("video-downloader 元数据必须是 JSON 对象")

    media_dir = output_root / "media"
    metadata_dir = output_root / "metadata"
    media_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    stable_video_path = media_dir / "source_video"
    if stable_video_path.exists():
        raise FileExistsError(f"目标视频已存在，拒绝覆盖：{stable_video_path}")
    shutil.move(str(video_path), stable_video_path)

    source_metadata_path = metadata_dir / "source_metadata.json"
    shutil.copy2(metadata_path, source_metadata_path)
    normalized_metadata_path = metadata_dir / "metadata.full.json"
    normalized_metadata_path.write_text(
        json.dumps(_normalized_metadata(raw_metadata), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    caption_value = result.get("post_caption_path") or result.get("caption_path")
    if caption_value:
        caption_path = _require_file(caption_value, "发布文案文件")
        shutil.copy2(caption_path, metadata_dir / "post_caption.txt")

    manifest = {
        "platform": str(result.get("platform") or "unknown"),
        "source_id": str(result.get("id") or "unknown"),
        "video_path": str(stable_video_path),
        "metadata_path": str(normalized_metadata_path),
        "source_metadata_path": str(source_metadata_path),
    }
    (output_root / "source_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def _default_downloader_script() -> Path:
    configured = os.environ.get("VIDEO_NOTE_DOWNLOADER_SCRIPT", "").strip()
    candidate = Path(configured) if configured else Path.home() / ".codex" / "skills" / "video-downloader" / "scripts" / "download_video.py"
    if not candidate.is_file():
        raise FileNotFoundError(
            "未找到 video-downloader。请设置 VIDEO_NOTE_DOWNLOADER_SCRIPT，"
            "或安装到 ~/.codex/skills/video-downloader。"
        )
    return candidate


def download_source(url: str, output_root: Path, downloader_script: Path | None = None) -> dict[str, str]:
    """下载单个网络视频且禁止下载器执行 ASR，再整理为本流水线输入。"""
    script = downloader_script or _default_downloader_script()
    download_root = output_root / "source"
    completed = subprocess.run(
        build_video_downloader_command(
            url,
            str(download_root),
            str(script),
            python_executable=sys.executable,
        ),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "无错误输出"
        raise RuntimeError(f"video-downloader 下载失败：{detail}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("video-downloader 未返回可解析 JSON 结果") from exc
    if not isinstance(result, dict):
        raise RuntimeError("video-downloader 返回结果不是 JSON 对象")
    return import_downloader_result(result, output_root)
