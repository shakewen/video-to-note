from __future__ import annotations

from html import escape
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


BADGES = {
    "sop": "[操作SOP]",
    "concept": "[深度解构]",
    "decision": "[对比决策]",
    "brief": "[极简速报]",
}


def render_cognitive_html(title: str, metadata: dict[str, Any], chapters: list[dict[str, Any]]) -> str:
    source_url = str(metadata.get("source_url", "") or "")
    cards = "\n".join(_render_chapter(chapter, source_url) for chapter in chapters)
    toc = "".join(
        f'<a href="#chapter-{index}"><span>{index:02d}</span>{escape(str(chapter.get("title", "未命名章节")))}</a>'
        for index, chapter in enumerate(chapters, 1)
    )
    distribution = {kind: sum(1 for item in chapters if item.get("template_type") == kind) for kind in BADGES}
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>{escape(title)}</title>
<style>
:root{{--ink:#26363a;--muted:#6b7779;--accent:#256d85;--soft:#e7f2f4;--paper:#fffdfa;--bg:#edf0ed;--line:#c9dadd;--warning:#fff0df;--warning-line:#dc8a43;--risk:#a74d47;}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:"JetBrains Mono","Microsoft YaHei",monospace;line-height:1.72;letter-spacing:0}}main{{width:min(1020px,calc(100% - 28px));margin:28px auto 72px}}.hero,.chapter{{background:var(--paper);border:1px solid #d7dfdc;border-radius:8px;box-shadow:0 8px 26px rgba(38,54,58,.055)}}
.hero{{padding:38px}}.eyebrow{{font-size:12px;font-weight:800;color:var(--accent)}}h1{{font-size:34px;line-height:1.25;margin:10px 0}}.intro{{color:var(--muted);max-width:800px}}.metrics{{display:grid;grid-template-columns:2fr repeat(4,1fr);gap:10px;margin-top:24px}}.metric{{padding:13px;background:var(--soft);border:1px solid var(--line);border-radius:6px}}.metric b{{display:block;font-size:11px;color:var(--accent)}}.metric strong{{display:block;margin-top:5px;font-size:18px}}.toc{{display:grid;grid-template-columns:1fr 1fr;gap:5px 18px;margin-top:22px}}.toc a{{display:flex;gap:10px;padding:7px 0;border-bottom:1px solid #e1e6e2;color:var(--ink);font-size:12px;text-decoration:none}}.toc span{{color:var(--accent);font-weight:900}}
.chapter{{margin-top:22px;padding:34px}}.chapter-head{{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;border-bottom:1px solid #dce5e3;padding-bottom:16px}}.chapter-head h2{{font-size:24px;line-height:1.35;margin:0}}.badge{{flex:none;padding:5px 10px;border-radius:4px;background:#f4cd62;color:#26363a;font-size:12px;font-weight:900;box-shadow:0 0 0 2px rgba(244,205,98,.18)}}.time{{font-size:12px;margin-top:7px}}.time a{{color:var(--accent)}}.plain{{font-size:18px;font-weight:800;line-height:1.55;margin:22px 0;padding-left:16px;border-left:4px solid var(--accent)}}mark{{background:#d9ebef;color:inherit;padding:0 2px}}
.sop-table,.decision-table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:11px;border:1px solid #d7e1df;text-align:left;vertical-align:top}}th{{background:var(--accent);color:#fff}}.warning{{margin-top:16px;padding:15px 18px;background:var(--warning);border-left:5px solid var(--warning-line)}}.warning b{{color:#9c5625}}.metaphor{{display:grid;grid-template-columns:150px 1fr;gap:14px;padding:16px;background:#f4efe7;border:1px solid #e2d8ca}}.metaphor b{{color:#806444}}.concept-callout{{margin-top:14px;padding:16px 18px;background:var(--soft);border-left:5px solid var(--accent)}}.decision-table td:nth-child(2){{background:#fff1ee;color:#823c37}}.decision-table td:nth-child(3){{background:#edf6f2;color:#285a4e}}.brief-callout{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}}.brief-callout div{{padding:18px;background:var(--soft);border:1px solid var(--line)}}
figure{{margin:0}}.diagram{{margin-top:20px}}.diagram svg{{display:block;width:100%;height:auto}}.svg-title,.svg-label,.svg-small,.svg-kicker{{font-family:"JetBrains Mono","Microsoft YaHei",monospace;fill:#29464d}}.svg-title{{font-size:17px;font-weight:900;fill:#256d85}}.svg-label{{font-size:14px;font-weight:800}}.svg-small{{font-size:12px}}.svg-kicker{{font-size:10px;fill:#6a858b}}figcaption{{font-size:12px;color:var(--muted);margin-top:7px}}.frame{{margin-top:20px}}.frame img{{display:block;width:100%;aspect-ratio:16/9;object-fit:contain;background:#111;border:1px solid #cfd8d6;border-radius:4px}}.facts{{margin-top:16px;border:1px solid #dce4e2;background:#fafcfb}}.facts summary{{cursor:pointer;padding:11px 14px;color:var(--accent);font-weight:800}}.facts ul{{margin:0;padding:0 34px 16px}}.facts li{{margin:6px 0}}.quote{{margin:16px 0 0;padding:12px 16px;background:#f4efe7;border-left:4px solid #9a8067}}
@media(max-width:720px){{main{{width:calc(100% - 16px);margin-top:8px}}.hero,.chapter{{padding:20px}}h1{{font-size:27px}}.metrics,.toc,.brief-callout{{grid-template-columns:1fr}}.chapter-head{{display:block}}.badge{{display:inline-block;margin-top:10px}}.metaphor{{grid-template-columns:1fr}}.table-wrap{{overflow-x:auto}}}}
</style></head><body><main><section class="hero"><div class="eyebrow">DYNAMIC COGNITIVE VIDEO NOTE</div><h1>{escape(title)}</h1><p class="intro">按原视频知识属性动态组织：操作看步骤，概念看原理，选型看取舍，轻内容只保留观点。所有细节均可回到对应时间戳核对。</p><div class="metrics"><div class="metric"><b>视频作者</b><strong>{escape(str(metadata.get('uploader') or '未提供'))}</strong></div><div class="metric"><b>章节</b><strong>{len(chapters)}</strong></div><div class="metric"><b>操作 SOP</b><strong>{distribution['sop']}</strong></div><div class="metric"><b>深度解构</b><strong>{distribution['concept']}</strong></div><div class="metric"><b>决策 / 观点</b><strong>{distribution['decision']} / {distribution['brief']}</strong></div></div><nav class="toc">{toc}</nav></section>{cards}</main></body></html>'''


def _render_chapter(chapter: dict[str, Any], source_url: str) -> str:
    index = int(chapter.get("chapter_index") or 0)
    kind = str(chapter.get("template_type", "sop"))
    title = escape(str(chapter.get("title", "未命名章节")))
    summary = _signal(str(chapter.get("plain_summary", "")))
    payload = chapter.get("template_data") or {}
    if kind == "sop":
        content = _render_sop(payload)
    elif kind == "concept":
        content = _render_concept(payload)
    elif kind == "decision":
        content = _render_decision(payload)
    else:
        content = _render_brief(payload)
    diagram = ""
    if kind != "brief" and chapter.get("svg"):
        diagram = f'<figure class="diagram">{chapter["svg"]}<figcaption>图解 · {escape(BADGES[kind].strip("[]"))}</figcaption></figure>'
    details = chapter.get("detail_restoration") or chapter.get("body") or []
    facts = "".join(f"<li>{_signal(str(item))}</li>" for item in details)
    quote = chapter.get("key_quote") or chapter.get("quote")
    quote_html = f'<blockquote class="quote">“{_signal(str(quote))}”</blockquote>' if quote else ""
    return f'''<article class="chapter template-{kind}" id="chapter-{index}"><header class="chapter-head"><div><h2>{title}</h2><div class="time">{_timestamp_link(str(chapter.get('time_range','')), source_url, '回看原视频')}</div></div><span class="badge">{BADGES[kind]}</span></header><p class="plain">{summary}</p>{content}{diagram}{_render_frame(chapter.get('frame'), source_url)}<details class="facts"><summary>展开原视频细节证据</summary><ul>{facts}</ul>{quote_html}</details></article>'''


def _render_sop(payload: dict[str, Any]) -> str:
    rows = "".join(f'<tr><td>{index}</td><td><b>{escape(str(step.get("action", "")))}</b></td><td>{_signal(str(step.get("detail", "")))}</td><td>{_signal(str(step.get("parameters", "")))}</td></tr>' for index, step in enumerate(payload.get("steps", []), 1))
    return f'<div class="table-wrap"><table class="sop-table"><thead><tr><th>顺序</th><th>动作</th><th>执行细节</th><th>关键参数与检查点</th></tr></thead><tbody>{rows}</tbody></table></div><aside class="warning"><b>避坑警告</b><br>{_signal(str(payload.get("warning", "")))}</aside>'


def _render_concept(payload: dict[str, Any]) -> str:
    return f'<div class="metaphor"><b>费曼日常大比喻</b><span>{_signal(str(payload.get("metaphor", "")))}</span></div><aside class="concept-callout"><b>底层逻辑说透</b><br>{_signal(str(payload.get("logic", "")))}</aside>'


def _render_decision(payload: dict[str, Any]) -> str:
    rows = "".join(f'<tr><td>{escape(str(row.get("option", "")))}</td><td>{_signal(str(row.get("avoid", "")))}</td><td>{_signal(str(row.get("recommend", "")))}</td></tr>' for row in payload.get("options", []))
    return f'<div class="table-wrap"><table class="decision-table"><thead><tr><th>方案 / 参数配置</th><th>绝对不要做</th><th>正确姿势</th></tr></thead><tbody>{rows}</tbody></table></div>'


def _render_brief(payload: dict[str, Any]) -> str:
    return f'<div class="brief-callout"><div><b>主讲人态度</b><p>{_signal(str(payload.get("attitude", "")))}</p></div><div><b>与后文 / 行动的绑定</b><p>{_signal(str(payload.get("next", "")))}</p></div></div>'


def _render_frame(frame: dict[str, Any] | None, source_url: str) -> str:
    if not frame:
        return ""
    src = escape(str(frame.get("src", "")), quote=True)
    timestamp = str(frame.get("timestamp", ""))
    return f'<figure class="frame"><img class="video-frame" src="{src}" alt="原视频 {escape(timestamp)} 画面" loading="lazy"><figcaption>{_timestamp_link(timestamp, source_url, "视频时间戳")}</figcaption></figure>'


def _timestamp_link(label: str, source_url: str, prefix: str) -> str:
    start = label.split("-", 1)[0]
    seconds = _timestamp_seconds(start)
    if seconds is None or not source_url:
        return f"{escape(prefix)}：{escape(label)}"
    parts = urlsplit(source_url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "t"]
    query.append(("t", str(seconds)))
    href = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return f'{escape(prefix)}：<a href="{escape(href, quote=True)}" target="_blank" rel="noopener">{escape(label)}</a>'


def _timestamp_seconds(value: str) -> int | None:
    parts = value.strip().split(":")
    if len(parts) not in (2, 3) or not all(item.isdigit() for item in parts):
        return None
    numbers = [int(item) for item in parts]
    return numbers[0] * 60 + numbers[1] if len(numbers) == 2 else numbers[0] * 3600 + numbers[1] * 60 + numbers[2]


def _signal(value: str) -> str:
    rendered = escape(value)
    for keyword in ("必须", "不要", "风险", "成本", "参数", "Seedance 2.0", "720p", "1080p", "21:9", "0.1", "0.2"):
        rendered = rendered.replace(escape(keyword), f"<mark><strong>{escape(keyword)}</strong></mark>")
    return rendered
