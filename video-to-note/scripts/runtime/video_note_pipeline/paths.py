from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OutputPaths:
    root: Path
    metadata: Path
    media: Path
    transcript: Path
    html: Path
    frames: Path
    render_check: Path


def build_output_paths(output_root: Path, video_id: str) -> OutputPaths:
    root = output_root / video_id
    html = root / "html"
    return OutputPaths(
        root=root,
        metadata=root / "metadata",
        media=root / "media",
        transcript=root / "transcript",
        html=html,
        frames=html / "frames",
        render_check=root / "render-check",
    )
