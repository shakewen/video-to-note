import os
from pathlib import Path
from typing import Any


CookieSpec = str | dict[str, Any]


def _tool_path(environment_name: str, fallback: str) -> str:
    configured = os.environ.get(environment_name, "").strip()
    return configured or fallback


def build_cookie_args(cookies: CookieSpec) -> list[str]:
    if isinstance(cookies, str):
        return ["--cookies", cookies]

    mode = cookies.get("mode", "file")
    if mode == "none":
        return []
    if mode == "optional_file":
        cookie_path = str(cookies.get("file_path", ""))
        return ["--cookies", cookie_path] if cookie_path and Path(cookie_path).is_file() else []
    if mode == "browser":
        return ["--cookies-from-browser", str(cookies.get("browser", "chrome"))]
    return ["--cookies", str(cookies.get("file_path", "./cookies.txt"))]


def build_metadata_command(url: str, cookies: CookieSpec, metadata_dir: str) -> list[str]:
    return [
        _tool_path("VIDEO_NOTE_YT_DLP", "yt-dlp"),
        *build_cookie_args(cookies),
        "--no-playlist",
        "--dump-single-json",
        "--write-thumbnail",
        "--write-description",
        "--write-info-json",
        "--skip-download",
        "--paths",
        metadata_dir,
        url,
    ]


def build_audio_command(url: str, cookies: CookieSpec, media_dir: str) -> list[str]:
    return [
        _tool_path("VIDEO_NOTE_YT_DLP", "yt-dlp"),
        *build_cookie_args(cookies),
        "--no-playlist",
        "-f",
        "ba/bestaudio/best",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--paths",
        media_dir,
        "--output",
        "audio.%(ext)s",
        url,
    ]


def build_video_command(url: str, cookies: CookieSpec, media_dir: str) -> list[str]:
    return [
        _tool_path("VIDEO_NOTE_YT_DLP", "yt-dlp"),
        *build_cookie_args(cookies),
        "--no-playlist",
        "-f",
        "bv*+ba/best",
        "--merge-output-format",
        "mp4",
        "--paths",
        media_dir,
        "--output",
        "video.%(ext)s",
        url,
    ]


def build_local_audio_command(source_path: str, output_mp3: str) -> list[str]:
    return [
        _tool_path("VIDEO_NOTE_FFMPEG", "ffmpeg"),
        "-y",
        "-i",
        source_path,
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "0",
        output_mp3,
    ]


def build_whisper_command(audio_path: str, language: str, transcript_dir: str) -> list[str]:
    model = "small.en" if language == "en" else "turbo"
    normalized_language = "en" if language == "en" else "zh"
    backend = os.environ.get(
        "VIDEO_NOTE_TRANSCRIBE_BACKEND",
        "openai-whisper",
    ).strip().lower()
    model_root = Path(
        os.environ.get("VIDEO_NOTE_HOME", str(Path.home() / ".video-note-runtime"))
    ) / "cache" / "whisper"

    if backend in {"faster-whisper", "faster_whisper"}:
        python = _tool_path("VIDEO_NOTE_PYTHON", "python")
        adapter = Path(__file__).with_name("transcribe.py")
        return [
            python,
            str(adapter),
            audio_path,
            "--backend",
            "faster-whisper",
            "--model",
            model,
            "--language",
            normalized_language,
            "--output-dir",
            transcript_dir,
            "--model-dir",
            str(model_root),
        ]

    command = [
        _tool_path("VIDEO_NOTE_WHISPER", "whisper"),
        audio_path,
        "--model",
        model,
    ]
    if normalized_language != "en":
        command.extend(["--language", normalized_language])
    command.extend(
        [
            "--task",
            "transcribe",
            "--output_format",
            "all",
            "--output_dir",
            transcript_dir,
            "--model_dir",
            str(model_root),
        ]
    )
    return command


def build_frame_command(video_path: str, timestamp: str, output_path: str) -> list[str]:
    return [
        _tool_path("VIDEO_NOTE_FFMPEG", "ffmpeg"),
        "-ss",
        timestamp,
        "-i",
        video_path,
        "-frames:v",
        "1",
        "-q:v",
        "1",
        output_path,
    ]


def build_ffprobe_duration_command(media_path: str) -> list[str]:
    return [
        _tool_path("VIDEO_NOTE_FFPROBE", "ffprobe"),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        media_path,
    ]


def build_chrome_screenshot_command(browser: str, html_path: str, output_png: str) -> list[str]:
    return [
        browser,
        "--headless=new",
        "--disable-gpu",
        f"--screenshot={output_png}",
        "--window-size=1440,2400",
        html_path,
    ]


def build_crop_command(input_png: str, output_png: str, width: int, height: int, y: int) -> list[str]:
    return [
        _tool_path("VIDEO_NOTE_FFMPEG", "ffmpeg"),
        "-i",
        input_png,
        "-vf",
        f"crop={width}:{height}:0:{y}",
        output_png,
    ]


def format_command(command: list[str]) -> str:
    formatted = []
    for item in command:
        if any(char.isspace() for char in item):
            formatted.append(f'"{item}"')
        else:
            formatted.append(item)
    return " ".join(formatted)
