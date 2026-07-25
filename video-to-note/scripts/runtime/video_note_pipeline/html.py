from html import escape
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def render_html(title: str, metadata: dict[str, Any], chapters: list[dict[str, Any]]) -> str:
    source_url = str(metadata.get("source_url", "") or "")
    chapter_html = "\n".join(_render_chapter_with_source(chapter, source_url) for chapter in chapters)
    metadata_html = _render_metadata(metadata)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
:root {{
  color-scheme: light;
  --paper: #f7f3ec;
  --ink: #202124;
  --muted: #68635c;
  --line: #ded7cc;
  --accent: #256d85;
  --accent-soft: #e7f2f4;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
  line-height: 1.72;
}}
main {{
  width: min(980px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 42px 0 72px;
}}
header {{
  border-bottom: 1px solid var(--line);
  margin-bottom: 28px;
  padding-bottom: 20px;
}}
h1 {{ font-size: 30px; margin: 0 0 12px; letter-spacing: 0; }}
h2 {{ font-size: 22px; margin: 34px 0 10px; letter-spacing: 0; }}
.meta, .time, figcaption {{ color: var(--muted); font-size: 14px; }}
.meta {{
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
}}
.meta-cover img {{
  width: min(360px, 100%);
  height: auto;
  display: block;
  border: 1px solid var(--line);
  border-radius: 8px;
}}
.meta-row strong {{ color: var(--ink); font-weight: 650; }}
.meta-description {{ margin: 0; color: var(--ink); }}
.chapter {{ padding: 18px 0 28px; border-bottom: 1px solid var(--line); }}
.body p {{ margin: 8px 0; }}
.quote {{
  margin: 14px 0;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.58);
  border-left: 4px solid var(--accent);
}}
.anchor {{ color: var(--muted); font-size: 14px; }}
figure {{ margin: 18px 0 0; }}
.diagram {{
  background: white;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  overflow-x: auto;
}}
.diagram svg {{ display: block; max-width: 100%; height: auto; margin: 0 auto; }}
.frame img {{
  width: 100%;
  height: auto;
  display: block;
  border: 1px solid var(--line);
  border-radius: 8px;
}}
</style>
</head>
<body>
<main>
<header>
<h1>{escape(title)}</h1>
{metadata_html}
</header>
{chapter_html}
</main>
</body>
</html>
"""


def _render_metadata(metadata: dict[str, Any]) -> str:
    if not metadata:
        return ""
    rows = []
    thumbnail = str(metadata.get("thumbnail", "") or "").strip()
    if thumbnail and _is_relative_asset(thumbnail):
        src = escape(thumbnail, quote=True)
        rows.append(f'<figure class="meta-cover"><img src="{src}" alt="封面"><figcaption>封面</figcaption></figure>')

    uploader = metadata.get("uploader")
    if uploader:
        rows.append(_meta_row("UP", str(uploader)))

    duration = metadata.get("duration")
    if duration:
        rows.append(_meta_row("时长", _format_duration(duration)))

    description = str(metadata.get("description", "") or "").strip()
    if description:
        rows.append(f'<p class="meta-description"><strong>简介：{escape(description)}</strong></p>')

    tags = _list_text(metadata.get("tags"), "、")
    if tags:
        rows.append(_meta_row("标签", tags))

    parts = _list_text(metadata.get("parts"), " / ")
    if parts:
        rows.append(_meta_row("分 P", parts))

    if thumbnail and not _is_relative_asset(thumbnail):
        rows.append(_meta_row("封面", thumbnail))

    source_url = metadata.get("source_url")
    if source_url:
        rows.append(_meta_row("原链接", str(source_url)))

    if not rows:
        return ""
    return f"<div class=\"meta\">{''.join(rows)}</div>"


def _meta_row(label: str, value: str) -> str:
    return f'<div class="meta-row"><strong>{escape(label)}：{escape(value)}</strong></div>'


def _list_text(value: Any, separator: str) -> str:
    if not isinstance(value, list):
        return ""
    items = [str(item).strip() for item in value if str(item).strip()]
    return separator.join(items)


def _is_relative_asset(path: str) -> bool:
    return not path.startswith(("http://", "https://", "file://", "/", "\\"))


def _format_duration(value: Any) -> str:
    try:
        total_seconds = int(float(value))
    except (TypeError, ValueError):
        return str(value)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _render_chapter(chapter: dict[str, Any]) -> str:
    return _render_chapter_with_source(chapter, "")


def _render_chapter_with_source(chapter: dict[str, Any], source_url: str) -> str:
    title = escape(str(chapter.get("title", "未命名章节")))
    time_range = str(chapter.get("time_range", ""))
    time_html = _render_timestamp_link(time_range, source_url, "回跳视频")
    body = "\n".join(f"<p>{escape(str(item))}</p>" for item in chapter.get("body", []))
    quote = chapter.get("quote")
    anchor = chapter.get("visual_anchor")
    svg = chapter.get("svg", "")
    frame = chapter.get("frame")

    quote_html = f"<blockquote class=\"quote\">{escape(str(quote))}</blockquote>" if quote else ""
    anchor_html = f"<p class=\"anchor\">视觉锚点：{escape(str(anchor))}</p>" if anchor else ""
    svg_html = f"""<figure class="diagram">
{svg}
<figcaption>图解：{title}</figcaption>
</figure>"""
    frame_html = _render_frame(frame, source_url)

    return f"""<section class="chapter">
<h2>{title}</h2>
<div class="time">{time_html}</div>
<div class="body">
{body}
{quote_html}
{anchor_html}
</div>
{svg_html}
{frame_html}
</section>"""


def _render_frame(frame: dict[str, Any] | None, source_url: str = "") -> str:
    if not frame:
        return ""
    src = escape(str(frame.get("src", "")), quote=True)
    timestamp = str(frame.get("timestamp", ""))
    timestamp_html = _render_timestamp_link(timestamp, source_url, "视频时间戳")
    timestamp_text = escape(timestamp)
    return f"""<figure class="frame">
<img src="{src}" alt="视频时间戳：{timestamp_text}">
<figcaption>{timestamp_html}</figcaption>
</figure>"""


def _render_timestamp_link(label: str, source_url: str, prefix: str) -> str:
    escaped_label = escape(label)
    seconds = _parse_timestamp_seconds(label)
    if not source_url or seconds is None:
        return f"{escape(prefix)}：{escaped_label}"
    href = escape(_with_timestamp(source_url, seconds), quote=True)
    return f'{escape(prefix)}：<a href="{href}" target="_blank" rel="noopener">{escaped_label}</a>'


def _parse_timestamp_seconds(value: str) -> int | None:
    start = value.split("-", 1)[0].strip()
    if not start:
        return None
    parts = start.split(":")
    if len(parts) not in (2, 3):
        return None
    if not all(part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def _with_timestamp(url: str, seconds: int) -> str:
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "t"]
    query.append(("t", str(seconds)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
