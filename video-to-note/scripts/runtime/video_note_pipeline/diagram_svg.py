from __future__ import annotations

from html import escape
from math import cos, pi, sin
from typing import Any


INK = "#24424b"
ACCENT = "#256d85"
SOFT = "#e7f2f4"
WARM = "#fff1df"


def render_diagram_spec(spec: Any) -> str:
    if not isinstance(spec, dict):
        return ""
    diagram_type = spec.get("type")
    if diagram_type == "flow":
        return _render_flow(spec)
    if diagram_type == "radial":
        return _render_radial(spec)
    if diagram_type == "matrix":
        return _render_matrix(spec)
    return ""


def _render_flow(spec: dict[str, Any]) -> str:
    nodes = [str(item) for item in spec.get("nodes", []) if str(item).strip()]
    if not nodes:
        return ""
    width, height = 760, 170
    box_width = min(150, max(96, (width - 70) // max(len(nodes), 1) - 28))
    gap = (width - 40 - box_width * len(nodes)) / max(len(nodes) - 1, 1)
    centers: dict[str, tuple[float, float]] = {}
    blocks = []
    for index, label in enumerate(nodes):
        x = 20 + index * (box_width + gap)
        centers[label] = (x + box_width / 2, 85)
        fill = SOFT if index % 2 == 0 else "#ffffff"
        blocks.append(
            f'<rect x="{x:.1f}" y="55" width="{box_width}" height="60" rx="6" fill="{fill}" stroke="{ACCENT}" stroke-width="1.5"/>'
            f'<text x="{x + box_width / 2:.1f}" y="90" text-anchor="middle" font-size="14" fill="{INK}" font-family="Microsoft YaHei">{_short(label)}</text>'
        )
    links = spec.get("links") or [[nodes[i], nodes[i + 1]] for i in range(len(nodes) - 1)]
    arrows = []
    for link in links:
        if not isinstance(link, list) or len(link) != 2:
            continue
        start, end = centers.get(str(link[0])), centers.get(str(link[1]))
        if not start or not end:
            continue
        direction = 1 if end[0] >= start[0] else -1
        arrows.append(
            f'<line x1="{start[0] + direction * box_width / 2:.1f}" y1="{start[1]:.1f}" '
            f'x2="{end[0] - direction * box_width / 2:.1f}" y2="{end[1]:.1f}" '
            f'stroke="{ACCENT}" stroke-width="2" marker-end="url(#arrow)"/>'
        )
    return _svg(width, height, "流程图", "".join(arrows + blocks), marker=True)


def _render_radial(spec: dict[str, Any]) -> str:
    center = str(spec.get("center") or "核心")
    branches = [str(item) for item in spec.get("branches", []) if str(item).strip()][:6]
    if not branches:
        return ""
    width, height = 760, 340
    cx, cy = width / 2, height / 2
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="62" fill="{ACCENT}"/>',
        f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" font-size="15" fill="#fff" font-family="Microsoft YaHei">{_short(center)}</text>',
    ]
    for index, label in enumerate(branches):
        angle = -pi / 2 + index * 2 * pi / len(branches)
        x, y = cx + cos(angle) * 250, cy + sin(angle) * 115
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="{ACCENT}" stroke-width="1.5"/>')
        parts.append(f'<rect x="{x - 68}" y="{y - 24}" width="136" height="48" rx="6" fill="{SOFT}" stroke="{ACCENT}"/>')
        parts.append(f'<text x="{x}" y="{y + 5}" text-anchor="middle" font-size="13" fill="{INK}" font-family="Microsoft YaHei">{_short(label)}</text>')
    return _svg(width, height, "关系图", "".join(parts))


def _render_matrix(spec: dict[str, Any]) -> str:
    width, height = 760, 380
    left, top, plot_width, plot_height = 95, 35, 610, 275
    parts = [
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" fill="#fff" stroke="#cbdadc"/>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="{INK}" stroke-width="2" marker-end="url(#arrow)"/>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left}" y2="{top}" stroke="{INK}" stroke-width="2" marker-end="url(#arrow)"/>',
        f'<text x="{left + plot_width / 2}" y="360" text-anchor="middle" font-size="14" fill="{INK}" font-family="Microsoft YaHei">{escape(str(spec.get("x_label", "X")))}</text>',
        f'<text x="25" y="{top + plot_height / 2}" text-anchor="middle" font-size="14" fill="{INK}" font-family="Microsoft YaHei" transform="rotate(-90 25 {top + plot_height / 2})">{escape(str(spec.get("y_label", "Y")))}</text>',
    ]
    for point in spec.get("points", []):
        if not isinstance(point, dict):
            continue
        try:
            x_value = max(0.0, min(100.0, float(point.get("x", 0))))
            y_value = max(0.0, min(100.0, float(point.get("y", 0))))
        except (TypeError, ValueError):
            continue
        x = left + plot_width * x_value / 100
        y = top + plot_height * (1 - y_value / 100)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{ACCENT}"/>')
        parts.append(f'<text x="{x + 12:.1f}" y="{y - 10:.1f}" font-size="13" fill="{INK}" font-family="Microsoft YaHei">{_short(point.get("label", ""))}</text>')
    return _svg(width, height, "对比矩阵", "".join(parts), marker=True)


def _svg(width: int, height: int, label: str, content: str, marker: bool = False) -> str:
    defs = (
        f'<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="{ACCENT}"/></marker></defs>'
        if marker else ""
    )
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">{defs}{content}</svg>'


def _short(value: Any, limit: int = 16) -> str:
    text = str(value).strip()
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return escape(text)
