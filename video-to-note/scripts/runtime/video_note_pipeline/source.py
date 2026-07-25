from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse, urlunparse


class SourceResolutionError(ValueError):
    pass


LOCAL_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".webm",
    ".m4v",
    ".flv",
    ".ts",
    ".mts",
    ".m2ts",
}

PLATFORM_COOKIES = {
    "bilibili": "./cookies/bilibili.txt",
    "douyin": "./cookies/douyin.txt",
    "youtube": "./cookies/youtube.txt",
}


@dataclass(frozen=True)
class VideoSource:
    platform: str
    source_kind: str
    source_id: str
    source_key: str
    input_value: str
    cookie_path: str | None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def resolve_source(value: str, cwd: str | Path | None = None) -> VideoSource:
    raw = str(value).strip().strip('"')
    if not raw:
        raise SourceResolutionError("视频链接或本地文件路径不能为空。")

    parsed = urlparse(raw)
    if parsed.scheme.lower() in {"http", "https"}:
        return _resolve_url(raw, parsed)
    return _resolve_local(raw, cwd)


def build_local_metadata(
    source_path: Path,
    probe: dict[str, Any],
    source_id: str,
) -> dict[str, Any]:
    format_data = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    format_tags = format_data.get("tags") if isinstance(format_data.get("tags"), dict) else {}
    title = str(format_tags.get("title") or source_path.stem)
    try:
        duration = float(format_data.get("duration"))
    except (TypeError, ValueError):
        duration = None
    return {
        "id": source_id,
        "title": title,
        "fulltitle": title,
        "uploader": None,
        "description": None,
        "tags": [],
        "thumbnail": None,
        "duration": duration,
        "webpage_url": source_path.resolve().as_uri(),
        "original_url": str(source_path.resolve()),
        "extractor": "local",
        "extractor_key": "LocalFile",
        "ext": source_path.suffix.lower().lstrip("."),
        "entries": [],
        "ffprobe": probe,
    }


def write_local_metadata(
    source_path: str | Path,
    output_path: str | Path,
    source_id: str,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    source = Path(source_path).resolve()
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(source),
    ]
    result = runner(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        message = str(result.stderr).strip() or "ffprobe 无法读取本地视频。"
        raise SourceResolutionError(message)
    try:
        probe = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SourceResolutionError("ffprobe 返回的本地视频信息不是有效 JSON。") from error

    metadata = build_local_metadata(source, probe, source_id)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def _resolve_url(raw: str, parsed) -> VideoSource:
    host = (parsed.hostname or "").lower()
    path = parsed.path or "/"

    if _host_matches(host, "bilibili.com") or host == "b23.tv":
        platform = "bilibili"
        match = re.search(r"BV[0-9A-Za-z]{10}", raw, re.IGNORECASE)
        source_id = match.group(0) if match else _url_fallback_id(raw)
    elif _host_matches(host, "youtube.com") or host == "youtu.be":
        platform = "youtube"
        query = parse_qs(parsed.query)
        if path.rstrip("/") == "/playlist" and not query.get("v"):
            raise SourceResolutionError("首版只处理单个视频，不处理 YouTube 播放列表。")
        source_id = _youtube_id(host, path, query) or _url_fallback_id(raw)
    elif _host_matches(host, "douyin.com") or _host_matches(host, "iesdouyin.com"):
        platform = "douyin"
        match = re.search(r"/video/(\d+)", path)
        source_id = match.group(1) if match else _url_fallback_id(raw)
    else:
        raise SourceResolutionError(f"暂不支持这个网站：{host or raw}")

    return VideoSource(
        platform=platform,
        source_kind="online_url",
        source_id=source_id,
        source_key=f"{platform}_{source_id}",
        input_value=raw,
        cookie_path=PLATFORM_COOKIES[platform],
    )


def _resolve_local(raw: str, cwd: str | Path | None) -> VideoSource:
    base = Path(cwd) if cwd is not None else Path.cwd()
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve()

    if path.is_dir():
        raise SourceResolutionError(f"本地路径是文件夹，不是视频文件：{path}")
    if not path.is_file():
        raise SourceResolutionError(f"本地视频文件不存在：{path}")
    if path.suffix.lower() not in LOCAL_VIDEO_EXTENSIONS:
        raise SourceResolutionError(f"暂不支持这个本地视频格式：{path.suffix or '无扩展名'}")

    stem = re.sub(r"[^\w.-]+", "-", path.stem, flags=re.UNICODE).strip("-._") or "video"
    stem = stem[:48]
    digest = sha256(str(path).lower().encode("utf-8")).hexdigest()[:8]
    source_id = f"{stem}-{digest}"
    return VideoSource(
        platform="local",
        source_kind="local_file",
        source_id=source_id,
        source_key=f"local_{source_id}",
        input_value=str(path),
        cookie_path=None,
    )


def _youtube_id(host: str, path: str, query: dict[str, list[str]]) -> str | None:
    if host == "youtu.be":
        return path.strip("/").split("/")[0] or None
    if query.get("v"):
        return query["v"][0]
    match = re.match(r"/(?:shorts|embed|live)/([^/?#]+)", path)
    return match.group(1) if match else None


def _url_fallback_id(raw: str) -> str:
    parsed = urlparse(raw)
    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            (parsed.hostname or "").lower(),
            parsed.path.rstrip("/") or "/",
            "",
            parsed.query,
            "",
        )
    )
    return f"url-{sha256(normalized.encode('utf-8')).hexdigest()[:10]}"


def _host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith(f".{domain}")
