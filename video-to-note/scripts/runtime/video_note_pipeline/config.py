from copy import deepcopy
from typing import Any


class ConfigError(ValueError):
    pass


VALID_LANGUAGES = {"zh", "en", "mixed"}
VALID_COOKIE_MODES = {"file", "optional_file", "browser", "none"}
VALID_VIDEO_TYPES = {"ui_demo", "lecture", "interview", "mixed"}
VALID_NOTE_MODES = {"source-faithful"}


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(config)

    video = _require_section(normalized, "video")
    cookies = _require_section(normalized, "cookies")
    language = _require_section(normalized, "language")
    frames = _require_section(normalized, "frames")
    output = _require_section(normalized, "output")
    note = normalized.setdefault("note", {"mode": "source-faithful"})
    if not isinstance(note, dict):
        raise ConfigError("note section 必须是对象")

    if not str(video.get("url", "")).strip():
        raise ConfigError("video.url is required")
    if not str(video.get("expected_id", "")).strip():
        raise ConfigError("video.expected_id is required")

    cookie_mode = cookies.get("mode", "file")
    if cookie_mode not in VALID_COOKIE_MODES:
        raise ConfigError(f"cookies.mode must be one of {sorted(VALID_COOKIE_MODES)}")
    if cookie_mode in {"file", "optional_file"} and not str(cookies.get("file_path", "")).strip():
        raise ConfigError(f"cookies.file_path is required when cookies.mode is {cookie_mode}")
    if cookie_mode == "browser" and not str(cookies.get("browser", "")).strip():
        raise ConfigError("cookies.browser is required when cookies.mode is browser")

    primary_language = language.get("primary", "zh")
    if primary_language not in VALID_LANGUAGES:
        raise ConfigError(f"language.primary must be one of {sorted(VALID_LANGUAGES)}")

    video_type = frames.get("video_type")
    if video_type not in VALID_VIDEO_TYPES:
        raise ConfigError(f"frames.video_type must be one of {sorted(VALID_VIDEO_TYPES)}")

    if not str(output.get("root_dir", "")).strip():
        raise ConfigError("output.root_dir is required")

    note_mode = note.get("mode", "source-faithful")
    if note_mode not in VALID_NOTE_MODES:
        raise ConfigError(f"note.mode must be one of {sorted(VALID_NOTE_MODES)}")
    note["mode"] = note_mode

    return normalized


def _require_section(config: dict[str, Any], name: str) -> dict[str, Any]:
    section = config.get(name)
    if not isinstance(section, dict):
        raise ConfigError(f"{name} section is required")
    return section
