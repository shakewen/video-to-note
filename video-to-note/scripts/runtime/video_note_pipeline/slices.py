import json
from pathlib import Path
from typing import Any

from .commands import build_crop_command, format_command
from .render_check import inspect_png, plan_crop_slices


def crop_commands_from_png(
    input_png: Path,
    output_dir: Path,
    slice_height: int = 1800,
    overlap: int = 100,
) -> list[list[str]]:
    info = inspect_png(input_png)
    slices = plan_crop_slices(
        total_height=int(info["height"]),
        viewport_width=int(info["width"]),
        slice_height=slice_height,
        overlap=overlap,
    )
    commands = []
    for item in slices:
        output_png = output_dir / f"slice_{item['index']:03d}.png"
        commands.append(
            build_crop_command(
                str(input_png),
                str(output_png),
                item["width"],
                item["height"],
                item["y"],
            )
        )
    return commands


def slice_manifest_from_png(
    input_png: Path,
    slice_height: int = 1800,
    overlap: int = 100,
) -> dict[str, Any]:
    info = inspect_png(input_png)
    slices = plan_crop_slices(
        total_height=int(info["height"]),
        viewport_width=int(info["width"]),
        slice_height=slice_height,
        overlap=overlap,
    )
    return {
        "input_png": str(input_png),
        "fullpage_width": int(info["width"]),
        "fullpage_height": int(info["height"]),
        "slice_height": slice_height,
        "overlap": overlap,
        "slices": [
            {
                **item,
                "output": f"slice_{item['index']:03d}.png",
            }
            for item in slices
        ],
    }


def write_slice_manifest(
    input_png: Path,
    output_path: Path,
    slice_height: int = 1800,
    overlap: int = 100,
) -> dict[str, Any]:
    manifest = slice_manifest_from_png(input_png, slice_height=slice_height, overlap=overlap)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def plan_crop_command_report(
    input_png: Path,
    output_dir: Path,
    slice_height: int = 1800,
    overlap: int = 100,
) -> str:
    commands = crop_commands_from_png(input_png, output_dir, slice_height=slice_height, overlap=overlap)
    lines = [
        "# Crop Slice Commands",
        "",
        f"- input_png: {input_png}",
        f"- output_dir: {output_dir}",
        f"- slice_height: {slice_height}",
        f"- overlap: {overlap}",
        "",
    ]
    lines.extend(f"`{format_command(command)}`" for command in commands)
    lines.append("")
    lines.append(
        "After generating slices, write `slice_manifest.json` with "
        "`./pipeline/run_pipeline.ps1 write-slice-manifest <fullpage.png> <render-check/slice_manifest.json>`."
    )
    lines.append("Review every slice manually and adjust y offsets if a chapter title, SVG, or key screenshot is cut.")
    return "\n".join(lines) + "\n"
