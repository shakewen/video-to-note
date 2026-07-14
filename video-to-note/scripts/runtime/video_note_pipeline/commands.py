from typing import Any
from pathlib import Path


CookieSpec = str | dict[str, Any]


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
        "yt-dlp",
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
        "yt-dlp",
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
        "yt-dlp",
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
        "ffmpeg",
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
    if language == "en":
        model = "small.en"
        return [
            "whisper",
            audio_path,
            "--model",
            model,
            "--task",
            "transcribe",
            "--output_format",
            "all",
            "--output_dir",
            transcript_dir,
        ]

    model = "turbo"
    return [
        "whisper",
        audio_path,
        "--model",
        model,
        "--language",
        "zh",
        "--task",
        "transcribe",
        "--output_format",
        "all",
        "--output_dir",
        transcript_dir,
    ]


def build_frame_command(video_path: str, timestamp: str, output_path: str) -> list[str]:
    return [
        "ffmpeg",
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
        "ffprobe",
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
        "ffmpeg",
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
