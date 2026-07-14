from __future__ import annotations

from html import escape
from math import ceil
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .diagram_svg import render_diagram_spec


BADGES = {
    "video_source": "视频原内容",
    "official_source": "官方资料补充",
    "third_party_source": "第三方经验",
    "ai_teaching": "AI 教学补充",
    "transfer_exercise": "迁移练习",
    "needs_confirmation": "待确认",
}
TOPOLOGY_LABELS = {
    "complete_course": "完整教学流程",
    "mixed_course": "完整流程 + 穿插技巧",
    "fragmented_knowledge": "独立知识合集",
}
THEMES = {
    "reference-warm": "--page-bg:#f7f4ed;--paper:#fffefa;--line:#e5ded2;--accent:#256d85;--accent-dark:#174e60;--soft:#eef5f3",
    "calm-blue": "--page-bg:#eef3f5;--paper:#ffffff;--line:#d5e1e5;--accent:#316f83;--accent-dark:#245363;--soft:#e7f2f4",
    "clean-gray": "--page-bg:#f1f2f2;--paper:#ffffff;--line:#dfe2e1;--accent:#4d666c;--accent-dark:#2f464b;--soft:#eef1f1",
}
TEMPLATE_LABELS = {
    "sop": "操作 SOP",
    "concept": "深度概念",
    "matrix": "对比决策",
    "brief": "极简速报",
}


def render_actionable_html(title: str, metadata: dict[str, Any], payload: dict[str, Any]) -> str:
    chapters = payload.get("chapters", [])
    stages = payload.get("learning_path", [])
    source_url = str(metadata.get("source_url") or "")
    sources = {item.get("id"): item for item in payload.get("sources", []) if isinstance(item, dict)}
    stage_by_chapter = {
        chapter_id: (index, stage)
        for index, stage in enumerate(stages, 1)
        for chapter_id in stage.get("chapter_ids", [])
    }
    cards = "".join(
        _render_chapter(chapter, sources, source_url, stage_by_chapter.get(chapter.get("chapter_id")))
        for chapter in chapters
    )
    source_list = "".join(_render_source(source) for source in payload.get("sources", []))
    dashboard = _render_dashboard(payload, chapters)
    toc = _render_toc(stages, {chapter.get("chapter_id"): chapter for chapter in chapters}, source_url)
    action_items = _render_action_items(payload.get("action_items"))
    topology = payload.get("content_topology", {})
    topology_label = TOPOLOGY_LABELS.get(str(topology.get("type")), str(topology.get("type") or "未确认"))
    theme = str(payload.get("visual_theme") or "reference-warm")
    if theme not in THEMES:
        theme = "reference-warm"
    theme_css = THEMES[theme]
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>{escape(title)}</title>
<style>
:root{{{theme_css};--ink:#263438;--muted:#697477;--warn:#fff1df;--practice:#eef3fb;--author:#edf6f2}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--page-bg);color:var(--ink);font-family:"Microsoft YaHei",Arial,sans-serif;line-height:1.72;letter-spacing:0}}main{{width:min(900px,calc(100% - 28px));margin:24px auto 56px;padding:0 34px;background:var(--paper);border:1px solid var(--line);border-radius:8px}}.hero,.ai-overview,.chapter-toc,.chapter,.sources{{margin:0;background:transparent}}.hero{{padding:34px 0 26px;border-bottom:1px solid var(--line)}}h1{{font-size:32px;line-height:1.3;margin:6px 0 10px}}h2{{font-size:24px;line-height:1.4;margin:0}}h3{{font-size:17px;margin:20px 0 8px}}p{{margin:7px 0}}a{{color:var(--accent-dark);text-decoration-thickness:1px;text-underline-offset:3px}}.eyebrow{{font-size:12px;font-weight:900;color:var(--accent)}}.topology{{color:var(--muted);margin-bottom:0}}
.global-dashboard{{padding:26px 0;border-bottom:1px solid var(--line)}}.dashboard-stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin:14px 0}}.dashboard-stat{{padding:11px 12px;background:var(--soft);border-top:3px solid var(--accent)}}.dashboard-stat b{{display:block;font-size:18px}}.dashboard-stat span{{font-size:12px;color:var(--muted)}}.ai-overview{{padding:18px 20px;border-left:5px solid var(--accent);background:#fff}}.ai-overview h2,.chapter-toc h2{{font-size:20px}}.summary-main{{font-size:19px;font-weight:800;max-width:850px}}.summary-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}}.summary-grid>div{{padding-top:10px;border-top:1px solid var(--line)}}.summary-grid ul{{margin:5px 0;padding-left:20px}}.knowledge-map{{margin:16px 0 0;padding:15px;background:#fff;border:1px solid var(--line);border-radius:6px}}.knowledge-map svg{{display:block;width:100%;height:auto}}
.chapter-toc{{padding:28px 0;border-bottom:1px solid var(--line)}}.toc-stage{{display:grid;grid-template-columns:180px 1fr;gap:18px;padding:17px 0;border-top:1px solid var(--line)}}.toc-stage:first-of-type{{margin-top:12px}}.toc-stage-title b{{display:block;color:var(--accent-dark)}}.toc-stage-title small{{color:var(--muted)}}.toc-links{{display:grid;grid-template-columns:1fr 1fr;gap:7px 18px}}.toc-item{{display:flex;justify-content:space-between;gap:10px;border-bottom:1px dotted var(--line);padding-bottom:5px}}.toc-time{{white-space:nowrap;font-size:12px}}
.chapter{{padding:36px 0;scroll-margin-top:12px;border-bottom:1px solid var(--line)}}.chapter-head{{display:flex;justify-content:space-between;gap:16px;padding-bottom:13px}}.chapter-number{{display:inline-block;min-width:34px;padding:3px 9px;margin-bottom:9px;border-radius:4px;background:#7656d6;color:#fff;font-size:12px;font-weight:900;text-align:center}}.chapter:nth-of-type(4n+2) .chapter-number{{background:#d04f58}}.chapter:nth-of-type(4n+3) .chapter-number{{background:#1598a0}}.chapter:nth-of-type(4n) .chapter-number{{background:#d08a32}}.stage-kicker{{display:block;color:var(--accent);font-size:12px;font-weight:900;margin-bottom:5px}}.unit-badge{{font-size:12px;font-weight:900;color:#fff;background:var(--accent);padding:4px 8px;border-radius:4px;height:max-content}}.chapter-jump{{font-size:12px;margin-top:5px}}.chapter-focus{{padding:15px 0 14px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}.chapter-focus strong{{display:block;font-size:20px;line-height:1.5;color:var(--accent-dark)}}.key-points{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:9px;list-style:none;padding:0;margin:11px 0 0}}.key-points li{{background:var(--soft);padding:10px 11px;border-left:3px solid var(--accent);font-size:14px}}
.context-grid,.result-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.context-grid>div,.verification,.troubleshooting{{padding:14px 16px;border:1px solid var(--line);background:#fff}}.operation-environment{{margin:14px 0 4px;padding:10px 13px;background:var(--soft);border-left:4px solid var(--accent);font-size:14px}}ol.steps{{padding-left:27px;margin-top:8px}}ol.steps li{{padding:8px 3px}}.source-badge{{display:inline-block;margin-left:8px;padding:1px 6px;border:1px solid currentColor;border-radius:4px;font-size:11px;font-weight:800;color:var(--accent)}}[data-source-kind="ai_teaching"]{{color:#806018}}[data-source-kind="third_party_source"]{{color:#8a4f45}}.tip{{margin:8px 0;padding:10px 14px;background:var(--warn);border-left:4px solid #d28a42}}
.author-example{{padding:15px 17px;border-left:4px solid #57957e;background:var(--author);margin-top:8px}}.example-text{{font-size:16px;font-weight:700;white-space:pre-wrap}}.example-meta{{color:var(--muted);font-size:12px}}.supplements{{margin-top:16px}}.supplement{{padding:11px 14px;border-left:3px solid #b8963e;background:#fffaf0;margin:7px 0}}.table-wrap{{overflow-x:auto;margin-top:10px}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:10px 11px;border:1px solid var(--line);text-align:left;vertical-align:top}}th{{background:var(--soft);color:var(--accent-dark)}}.sop-table td:first-child{{width:62px;font-weight:900;color:var(--accent)}}.visual-alignment{{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr);gap:16px;margin:14px 0;align-items:start}}.visual-alignment .frame{{margin:0}}.fact-panel{{padding:14px 16px;background:var(--soft);border-left:4px solid var(--accent)}}.feynman-card{{padding:15px 17px;background:#edf5f7;border-left:4px solid var(--accent);margin-top:12px}}.feynman-card dl{{display:grid;grid-template-columns:110px 1fr;gap:7px 12px;margin:8px 0 0}}.feynman-card dt{{font-weight:900}}.feynman-card dd{{margin:0}}.decision-matrix td:nth-child(2){{background:#fff3e8}}.decision-matrix td:nth-child(3){{background:#eef7f1}}.brief-card{{padding:14px 17px;background:#f6f3ed;border-left:4px solid #9a8f7a}}.action-items{{padding:30px 0;border-bottom:1px solid var(--line)}}
.verification,.troubleshooting{{margin-top:13px}}.verification ul,.troubleshooting ul{{margin:6px 0;padding-left:20px}}.diagram{{margin:18px 0 0;padding:18px;background:#fff;border:1px solid var(--line);border-radius:6px}}.diagram svg{{display:block;width:100%;height:auto}}.frame{{margin:18px 0 0}}.frame img{{display:block;width:100%;max-height:420px;object-fit:contain;background:#111;border-radius:4px}}figcaption{{font-size:12px;color:var(--muted);margin-top:7px}}details{{margin-top:13px;border-top:1px solid var(--line);padding-top:9px}}summary{{cursor:pointer;font-weight:800;color:var(--accent)}}.sources{{padding:26px 0 34px}}.sources ul{{padding-left:20px}}
@media(max-width:760px){{main{{width:100%;margin:0;padding:0 18px;border:0;border-radius:0}}.hero{{padding-top:24px}}h1{{font-size:26px}}.dashboard-stats,.summary-grid,.context-grid,.result-grid,.key-points,.toc-links,.visual-alignment{{grid-template-columns:1fr}}.toc-stage{{grid-template-columns:1fr;gap:8px}}.chapter-head{{display:block}}.unit-badge{{display:inline-block;margin-top:8px}}.feynman-card dl{{grid-template-columns:1fr}}}}
</style></head><body data-theme="{escape(theme)}"><main><header class="hero"><div class="eyebrow">ACTIONABLE VIDEO NOTE</div><h1>{escape(title)}</h1><p>作者：{escape(str(metadata.get('uploader') or '未提供'))}</p><p class="topology">内容结构：{escape(topology_label)} · {escape(str(topology.get('reason') or ''))}</p></header>{dashboard}{toc}{cards}{action_items}<section class="sources"><h2>资料来源</h2><ul>{source_list or '<li>本笔记暂无外部资料</li>'}</ul></section></main></body></html>'''


def _render_ai_overview(summary: Any) -> str:
    if not isinstance(summary, dict):
        return ""
    outcomes = "".join(f"<li>{escape(str(item))}</li>" for item in summary.get("learning_outcomes", []))
    return f'''<section class="ai-overview"><div class="eyebrow">AI 总结</div><div class="summary-grid"><div><b>看完你会掌握</b><ul>{outcomes}</ul></div><div><b>适合谁</b><p>{escape(str(summary.get('audience','')))}</p><b>最终产物</b><p>{escape(str(summary.get('final_deliverable','')))}</p></div></div></section>'''


def _render_dashboard(payload: dict[str, Any], chapters: list[dict[str, Any]]) -> str:
    text_parts: list[str] = []
    frame_count = 0
    for chapter in chapters:
        text_parts.extend(str(item) for item in chapter.get("body", []))
        text_parts.append(str(chapter.get("chapter_summary") or chapter.get("goal") or ""))
        text_parts.extend(
            str(item.get("text", ""))
            for item in chapter.get("source_operations", [])
            if isinstance(item, dict)
        )
        frame_count += len(chapter.get("evidence", []))
    word_count = len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+", " ".join(text_parts)))
    reading_minutes = max(1, ceil(word_count / 400))
    summary = payload.get("ai_summary") if isinstance(payload.get("ai_summary"), dict) else {}
    core_problem = escape(str(summary.get("core_problem") or "按原视频顺序完成学习与操作"))
    stats = (
        f'<div class="dashboard-stats"><div class="dashboard-stat"><b>{word_count}</b><span>有效字数</span></div>'
        f'<div class="dashboard-stat"><b>{len(chapters)}</b><span>自然章节</span></div>'
        f'<div class="dashboard-stat"><b>{frame_count}</b><span>视频截图</span></div>'
        f'<div class="dashboard-stat"><b>{reading_minutes} 分钟</b><span>建议阅读</span></div></div>'
    )
    branches = [
        str(stage.get("title"))
        for stage in payload.get("learning_path", [])
        if isinstance(stage, dict) and stage.get("title")
    ]
    if len(branches) < 2:
        branches = [str(chapter.get("title")) for chapter in chapters if chapter.get("title")]
    map_svg = render_diagram_spec({"type": "radial", "center": "视频主线", "branches": branches})
    knowledge_map = (
        f'<figure class="knowledge-map">{map_svg}<figcaption>章节关系图：按任务主线连接各学习节点</figcaption></figure>'
        if map_svg else ""
    )
    return f'<section class="global-dashboard"><div class="eyebrow">全局掌控</div><h2>视频核心矛盾</h2><p class="summary-main">{core_problem}</p>{stats}{_render_ai_overview(summary)}{knowledge_map}</section>'


def _render_toc(stages: list[dict[str, Any]], chapters: dict[str, dict[str, Any]], source_url: str) -> str:
    stage_html = []
    for index, stage in enumerate(stages, 1):
        links = []
        for chapter_id in stage.get("chapter_ids", []):
            chapter = chapters.get(chapter_id)
            if not chapter:
                continue
            timestamp = str(chapter.get("time_range", "")).split("-", 1)[0]
            jump = _video_link(source_url, timestamp, timestamp)
            links.append(f'<div class="toc-item"><a href="#{escape(chapter_id)}">{escape(str(chapter.get("chapter_index","")))}. {escape(str(chapter.get("title","")))}</a><span class="toc-time">{jump}</span></div>')
        stage_html.append(f'<section class="toc-stage"><div class="toc-stage-title"><b>阶段 {index} · {escape(str(stage.get("title","")))}</b><small>{escape(str(stage.get("deliverable","")))}</small></div><div class="toc-links">{"".join(links)}</div></section>')
    return f'<nav class="chapter-toc"><div class="learning-path"><div class="eyebrow">目录</div><h2>按原视频节奏一步步学习</h2>{"".join(stage_html)}</div></nav>'


def _badge(kind: str) -> str:
    return f'<span class="source-badge" data-source-kind="{escape(kind)}">{escape(BADGES.get(kind, kind))}</span>'


def _render_chapter(chapter: dict[str, Any], sources: dict[str, dict[str, Any]], source_url: str, stage_info: tuple[int, dict[str, Any]] | None) -> str:
    template_type = _chapter_template(chapter)
    first_timestamp = _chapter_timestamp(chapter)
    stage_label = f'阶段 {stage_info[0]} · {stage_info[1].get("title", "")}' if stage_info else "独立章节"
    summary = str(chapter.get("chapter_summary") or chapter.get("goal") or (chapter.get("body") or [""])[0])
    points = chapter.get("key_points") or chapter.get("verification", [])
    key_points = "".join(f"<li>{escape(str(item))}</li>" for item in points)
    point_list = f'<ul class="key-points">{key_points}</ul>' if key_points else ""
    focus = "" if template_type == "brief" else f'<section class="chapter-focus"><strong>{escape(summary)}</strong>{point_list}</section>'
    supplements = _render_supplements(chapter.get("teaching_supplements", []))
    author_examples = _render_author_examples(chapter, source_url, first_timestamp)
    verification = "".join(f"<li>{escape(str(item))}</li>" for item in chapter.get("verification", []))
    trouble = "".join(f'<li><b>{escape(str(item.get("symptom", "")))}</b>：{escape(str(item.get("check", "")))}</li>' if isinstance(item, dict) else f'<li>{escape(str(item))}</li>' for item in chapter.get("troubleshooting", []))
    tips = "".join(f'<aside class="tip">避坑：{escape(str(item.get("text", "")))}</aside>' for item in chapter.get("tips", []) if isinstance(item, dict))

    if template_type == "sop":
        environment_text = str(chapter.get("operation_environment") or "原视频未明确展示，待人工确认")
        environment = escape(environment_text)
        prerequisites = "".join(f'<li>{escape(str(item))}</li>' for item in chapter.get("prerequisites", []))
        rows = _render_sop_rows(chapter.get("source_operations", []), environment_text)
        content = f'''<p><b>本章目标：</b>{escape(str(chapter.get('goal','')))}</p><div class="operation-environment"><b>操作环境：</b>{environment}</div>{f'<h3>开始前准备</h3><ul>{prerequisites}</ul>' if prerequisites else ''}<h3>跟着作者操作</h3><div class="table-wrap"><table class="sop-table"><thead><tr><th>步骤</th><th>在哪里操作</th><th>具体动作</th><th>参数或结果</th></tr></thead><tbody>{rows}</tbody></table></div>{tips}{author_examples}{supplements}{_render_result_grid(verification, trouble)}'''
    elif template_type == "concept":
        rules = "".join(f"<li>{escape(str(item))}</li>" for item in chapter.get("decision_rules", []))
        check = f'<div class="verification"><b>理解检查</b><ul>{verification}</ul></div>' if verification else ""
        content = f'{_render_visual_alignment(chapter, source_url)}{_render_feynman(chapter.get("feynman_scaffolding"))}<h3>作者讲清的判断规则</h3><ul>{rules}</ul>{author_examples}{supplements}{check}'
    elif template_type == "matrix":
        rows = "".join(f'<tr><td>{escape(str(item.get("option", "")))}</td><td>{escape(str(item.get("avoid", "")))}</td><td>{escape(str(item.get("recommend", "")))}</td></tr>' for item in chapter.get("decision_matrix", []) if isinstance(item, dict))
        content = f'<p class="summary-main">{escape(str(chapter.get("tradeoff") or summary))}</p><div class="table-wrap"><table class="decision-matrix"><thead><tr><th>方案或配置</th><th>不要这样做</th><th>正确做法</th></tr></thead><tbody>{rows}</tbody></table></div>{author_examples}{supplements}'
    else:
        attitude = str(chapter.get("speaker_attitude") or "")
        paragraphs = "".join(f"<p>{escape(str(item))}</p>" for item in chapter.get("body", []))
        attitude_html = f'<p><b>主讲人态度：</b>{escape(attitude)}</p>' if attitude else ""
        content = f'<div class="brief-card">{paragraphs}{attitude_html}</div>'

    diagram_svg = render_diagram_spec(chapter.get("diagram_spec"))
    if not diagram_svg and template_type != "brief":
        diagram_svg = str(chapter.get("svg") or "")
    diagram = f'<figure class="diagram">{diagram_svg}<figcaption>图解：{escape(str(chapter.get("title", "")))}</figcaption></figure>' if diagram_svg else ""
    evidence = "" if template_type == "concept" else "".join(_render_evidence(item, source_url) for item in chapter.get("evidence", []))
    citations = "".join(_render_source(sources[cid]) for cid in chapter.get("citations", []) if cid in sources)
    details = "".join(f"<li>{escape(str(item))}</li>" for item in chapter.get("detail_restoration", []))
    chapter_number = escape(str(chapter.get("chapter_index", "")))
    return f'''<article class="chapter" id="{escape(str(chapter.get('chapter_id','')))}"><header class="chapter-head"><div><span class="chapter-number">第 {chapter_number} 章</span><span class="stage-kicker">{escape(stage_label)}</span><h2>{escape(str(chapter.get('title','')))}</h2><div class="chapter-jump">{_video_link(source_url, first_timestamp, '回到原片 '+first_timestamp)}</div></div><span class="unit-badge">{escape(TEMPLATE_LABELS[template_type])}</span></header>{focus}{content}{diagram}{evidence}<details><summary>展开视频细节与资料来源</summary><ul>{details}</ul><ul>{citations}</ul></details></article>'''


def _render_author_examples(chapter: dict[str, Any], source_url: str, fallback_timestamp: str) -> str:
    authored = chapter.get("author_examples") or []
    if not authored and chapter.get("original_examples"):
        authored = [{"label": "作者原例", "text": chapter["original_examples"][0], "timestamp": fallback_timestamp, "completeness": "根据视频内容整理；原视频未展示完整原文。"}]
    if not authored:
        return ""
    blocks = "".join(f'<div class="author-example"><b>{escape(str(item.get("label","作者原例")))}</b><p class="example-text">{escape(str(item.get("text","")))}</p><p class="example-meta">{escape(str(item.get("completeness","")))} · {_video_link(source_url, str(item.get("timestamp") or fallback_timestamp), "回看原例")}</p></div>' for item in authored if isinstance(item, dict))
    return f'<h3>作者原例</h3>{blocks}'


def _chapter_template(chapter: dict[str, Any]) -> str:
    explicit = str(chapter.get("template_type") or "")
    if explicit in TEMPLATE_LABELS:
        return explicit
    if chapter.get("decision_matrix"):
        return "matrix"
    return {"operation": "sop", "concept": "concept", "brief": "brief"}.get(
        str(chapter.get("unit_type")), "brief"
    )


def _render_sop_rows(items: list[Any], default_location: str) -> str:
    rows = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            continue
        location = str(item.get("location") or default_location)
        action = str(item.get("action") or item.get("text") or "")
        result = str(item.get("parameter_or_result") or "按视频画面确认结果")
        rows.append(
            f'<tr><td>{index}</td><td>{escape(location)}</td><td>{escape(action)} {_badge("video_source")}</td><td>{escape(result)}</td></tr>'
        )
    return "".join(rows)


def _render_result_grid(verification: str, trouble: str) -> str:
    blocks = []
    if verification:
        blocks.append(f'<div class="verification"><b>结果验收</b><ul>{verification}</ul></div>')
    if trouble:
        blocks.append(f'<div class="troubleshooting"><b>失败排查</b><ul>{trouble}</ul></div>')
    return f'<div class="result-grid">{"".join(blocks)}</div>' if blocks else ""


def _render_visual_alignment(chapter: dict[str, Any], source_url: str) -> str:
    evidence = [item for item in chapter.get("evidence", []) if isinstance(item, dict)]
    facts = list(chapter.get("visual_facts") or chapter.get("decision_rules") or [])
    if evidence:
        facts.insert(0, str(evidence[0].get("proves") or ""))
    fact_items = "".join(f'<li>{escape(str(item))}</li>' for item in facts if str(item).strip())
    frame = _render_evidence(evidence[0], source_url) if evidence else '<p>本章没有可验证的画面截图。</p>'
    return f'<div class="visual-alignment"><div>{frame}</div><div class="fact-panel"><b>画面事实</b><ul>{fact_items}</ul></div></div>'


def _render_feynman(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    rows = []
    for label, field in (("术语", "term"), ("一句定义", "definition"), ("生活比喻", "metaphor"), ("常见误区", "misconception")):
        text = str(value.get(field) or "").strip()
        if text:
            rows.append(f'<dt>{label}</dt><dd>{escape(text)}</dd>')
    return f'<aside class="feynman-card"><b>AI 通俗解释</b><dl>{"".join(rows)}</dl></aside>' if rows else ""


def _render_action_items(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return ""
    rows = "".join(
        f'<tr><td>{escape(str(item.get("who", "")))}</td><td>{escape(str(item.get("what", "")))}</td><td>{escape(str(item.get("when", "")))}</td><td>{escape(str(item.get("note", "")))}</td></tr>'
        for item in value if isinstance(item, dict)
    )
    if not rows:
        return ""
    return f'<section class="action-items"><div class="eyebrow">行动追踪</div><h2>视频明确提出的任务</h2><div class="table-wrap"><table><thead><tr><th>负责人</th><th>具体任务</th><th>截止时间</th><th>背景与备注</th></tr></thead><tbody>{rows}</tbody></table></div></section>'


def _render_supplements(items: list[Any]) -> str:
    blocks = "".join(f'<div class="supplement">{escape(str(item.get("text", "")))}{_badge(str(item.get("source_kind", "ai_teaching")))}</div>' for item in items if isinstance(item, dict))
    return f'<details class="supplements"><summary>展开 AI 与外部资料补充</summary>{blocks}</details>' if blocks else ""


def _render_evidence(item: dict[str, Any], source_url: str) -> str:
    timestamp = str(item.get("timestamp", ""))
    return f'<figure class="frame"><img class="video-frame" src="{escape(str(item.get("frame_src", "")))}" alt="视频证据"><figcaption>{_video_link(source_url, timestamp, "视频时间戳："+timestamp)} · 该截图证明：{escape(str(item.get("proves", "")))}</figcaption></figure>'


def _render_source(source: dict[str, Any]) -> str:
    title = escape(str(source.get("title", "未命名来源")))
    url = source.get("url")
    link = f'<a href="{escape(str(url))}">{title}</a>' if url else title
    checked = f'（查询：{escape(str(source.get("checked_at"))) }）' if source.get("checked_at") else ""
    return f'<li>{link}{_badge(str(source.get("kind", "needs_confirmation")))}{checked}</li>'


def _chapter_timestamp(chapter: dict[str, Any]) -> str:
    evidence = chapter.get("evidence") or []
    if evidence and isinstance(evidence[0], dict) and evidence[0].get("timestamp"):
        return str(evidence[0]["timestamp"])
    return str(chapter.get("time_range", "")).split("-", 1)[0]


def _video_link(source_url: str, timestamp: str, label: str) -> str:
    if not source_url:
        return escape(label)
    seconds = _timestamp_seconds(timestamp)
    if seconds is None:
        return escape(label)
    split = urlsplit(source_url)
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    query["t"] = str(seconds)
    href = urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))
    return f'<a href="{escape(href)}" target="_blank" rel="noopener">{escape(label)}</a>'


def _timestamp_seconds(value: str) -> int | None:
    try:
        parts = [int(part) for part in value.strip().split(":")]
    except ValueError:
        return None
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return None
