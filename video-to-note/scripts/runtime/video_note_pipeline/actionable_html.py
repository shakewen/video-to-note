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
ADAPTIVE_ROLE_LABELS = {
    "overview": "全局定位",
    "method": "方法拆解",
    "decision": "决策判断",
    "process": "过程复原",
    "case": "案例分析",
    "warning": "限制提醒",
    "conclusion": "结论收束",
}
AI_ADVICE_VERDICT_LABELS = {
    "correct": "观点正确",
    "partially_correct": "观点部分正确",
    "incorrect": "观点错误",
    "insufficient_evidence": "证据不足",
}


def render_actionable_html(title: str, metadata: dict[str, Any], payload: dict[str, Any]) -> str:
    if payload.get("learning_design_version") in {"b-c-v1", "adaptive-blocks-v1"}:
        return _render_learning_html(title, metadata, payload)

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


def _render_learning_html(
    title: str,
    metadata: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    """渲染旧版统一骨架或新版自适应内容块的完全离线长页。"""
    chapters = [
        chapter for chapter in payload.get("chapters", []) if isinstance(chapter, dict)
    ]
    source_url = str(metadata.get("source_url") or "")
    stages = [
        stage for stage in payload.get("learning_path", []) if isinstance(stage, dict)
    ]
    stage_by_chapter = {
        chapter_id: (index, stage)
        for index, stage in enumerate(stages, 1)
        for chapter_id in stage.get("chapter_ids", [])
    }
    nav_items = "".join(
        f'<a class="course-nav-link" href="#{escape(str(chapter.get("chapter_id", "")))}" '
        f'data-chapter-link="{escape(str(chapter.get("chapter_id", "")))}">'
        f'<span>{escape(str(chapter.get("chapter_index", ""))).zfill(2)}</span>'
        f'<b>{escape(str(chapter.get("title", "")))}</b></a>'
        for chapter in chapters
    )
    mobile_items = "".join(
        f'<a class="mobile-course-link" href="#{escape(str(chapter.get("chapter_id", "")))}">'
        f'{escape(str(chapter.get("chapter_index", "")))}. '
        f'{escape(str(chapter.get("title", "")))}</a>'
        for chapter in chapters
    )
    design_version = str(payload.get("learning_design_version") or "b-c-v1")
    if design_version == "adaptive-blocks-v1":
        ai_advice_enabled = payload.get("ai_advice_enabled")
        cards = "".join(
            _render_adaptive_chapter(
                chapter,
                source_url,
                stage_by_chapter.get(chapter.get("chapter_id")),
                ai_advice_enabled=ai_advice_enabled,
            )
            for chapter in chapters
        )
    else:
        cards = "".join(
            _render_learning_chapter(
                chapter,
                source_url,
                stage_by_chapter.get(chapter.get("chapter_id")),
            )
            for chapter in chapters
        )
    outcomes = payload.get("ai_summary", {}).get("learning_outcomes", [])
    outcome_items = "".join(
        f"<li>{escape(str(item))}</li>" for item in outcomes if str(item).strip()
    )
    if not outcome_items:
        outcome_items = (
            "<li>看懂作者使用的具体案例</li>"
            "<li>复原作者的方法与因果</li>"
            "<li>把方法替换成自己的内容</li>"
        )
    author = escape(str(metadata.get("uploader") or "原视频作者"))
    chapter_count = len(chapters)
    hero_kicker = (
        "按章节语义复原作者内容"
        if design_version == "adaptive-blocks-v1"
        else "从作者原例到直接应用"
    )
    footer_text = (
        "本页不包含答题、评分或答案提交；每章只呈现原视频确实支持的内容块。"
        if design_version == "adaptive-blocks-v1"
        else "本页不包含答题、评分或答案提交；请直接复原作者原例并迁移到自己的内容。"
    )
    return f'''<!doctype html>
<html lang="zh-CN" data-learning-design="{escape(design_version)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<link rel="icon" href="data:,">
<title>{escape(title)}</title>
<style>
:root{{--canvas:#f3f0e8;--paper:#fffdf8;--white:#ffffff;--plane:#f7f4ed;--ink:#262626;--muted:#746f67;--line:#d5d0c7;--accent:#8b765b;--accent-ink:#6f5d48;--danger:#8a4943;--danger-plane:#fbf1ef;--caution:#7a633b;--caution-plane:#f8f2e5}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--canvas);color:var(--ink);font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif;font-size:16px;line-height:1.75;text-rendering:optimizeLegibility}}a{{color:var(--accent-ink);text-decoration-thickness:1px;text-underline-offset:3px}}button,summary,a{{-webkit-tap-highlight-color:transparent}}.reading-track{{position:fixed;z-index:20;inset:0 0 auto;height:2px;background:var(--line)}}#reading-progress{{width:100%;height:100%;background:var(--accent);transform:scaleX(0);transform-origin:left center;transition:transform .15s linear}}.course-shell{{display:grid;grid-template-columns:244px minmax(0,920px);gap:28px;max-width:1240px;margin:0 auto;padding:32px 24px 80px}}.course-sidebar{{position:sticky;top:28px;align-self:start;max-height:calc(100vh - 56px);overflow:auto;padding:22px 10px 22px 20px;border-left:1px solid var(--line)}}.brand-kicker{{font-size:11px;letter-spacing:.16em;font-weight:800;color:var(--accent-ink)}}.course-sidebar h2{{margin:9px 0 5px;font-family:"Songti SC","SimSun",serif;font-size:19px;line-height:1.45}}.course-sidebar>p{{margin:0 0 20px;color:var(--muted);font-size:12px}}.course-sidebar nav{{position:relative}}.course-sidebar nav::before{{content:"";position:absolute;top:18px;bottom:18px;left:8px;width:1px;background:var(--line)}}.course-nav-link{{position:relative;display:grid;grid-template-columns:32px 1fr;gap:6px;align-items:start;padding:9px 7px;color:var(--muted);text-decoration:none;font-size:13px}}.course-nav-link::before{{content:"";position:absolute;z-index:1;top:16px;left:5px;width:7px;height:7px;border:1px solid var(--accent);border-radius:50%;background:var(--canvas)}}.course-nav-link span{{font-variant-numeric:tabular-nums;color:var(--accent-ink);text-align:right}}.course-nav-link b{{font-weight:600}}.course-nav-link:hover,.course-nav-link[aria-current="true"]{{color:var(--ink)}}.course-nav-link[aria-current="true"]::before{{background:var(--accent)}}.course-main{{min-width:0;background:var(--paper);border:1px solid var(--line)}}.course-hero{{padding:52px 54px 44px;border-bottom:1px solid var(--line)}}.eyebrow{{font-size:12px;font-weight:900;letter-spacing:.12em;color:var(--accent-ink)}}.course-hero h1{{max-width:760px;margin:9px 0 13px;font-family:"Songti SC","SimSun",serif;font-size:clamp(32px,4vw,48px);font-weight:700;line-height:1.22;letter-spacing:-.02em}}.hero-meta{{color:var(--muted);font-size:13px}}.hero-summary{{max-width:760px;margin:28px 0 0;padding:18px 0 0;border-top:1px solid var(--line)}}.hero-summary b{{display:block;margin-bottom:9px;font-size:13px;color:var(--accent-ink)}}.hero-summary ul{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:0;padding:0;list-style:none}}.hero-summary li{{position:relative;padding-left:16px;font-size:13px;color:var(--muted)}}.hero-summary li::before{{content:"";position:absolute;top:.72em;left:0;width:6px;height:6px;border-radius:50%;background:var(--accent)}}.mobile-course-nav{{display:none;margin:0;border-bottom:1px solid var(--line);background:var(--plane)}}.mobile-course-nav summary{{padding:14px 20px;font-weight:800;color:var(--accent-ink);cursor:pointer}}.mobile-course-links{{display:grid;padding:0 20px 14px}}.mobile-course-link{{padding:8px 0;border-top:1px dotted var(--line);text-decoration:none;font-size:14px}}.learning-chapter{{scroll-margin-top:18px;margin:0;padding:48px 54px;border-bottom:1px solid var(--line);background:var(--paper)}}.chapter-heading{{display:flex;justify-content:space-between;gap:22px;padding-bottom:23px;border-bottom:1px solid var(--line)}}.chapter-index{{display:inline-flex;padding:3px 8px;border:1px solid var(--accent);border-radius:2px;color:var(--accent-ink);font-size:11px;font-weight:900}}.role-badge{{display:inline-flex;margin-left:8px;padding:3px 8px;border-left:1px solid var(--line);color:var(--muted);font-size:11px;font-weight:800}}.stage-label{{display:block;margin-top:11px;color:var(--muted);font-size:12px}}.chapter-heading h2{{max-width:680px;margin:6px 0 0;font-family:"Songti SC","SimSun",serif;font-size:clamp(25px,3vw,34px);line-height:1.35}}.source-jump{{align-self:start;white-space:nowrap;font-size:12px}}.learning-question{{margin:26px 0;padding:18px 20px;border-top:1px solid var(--accent);border-bottom:1px solid var(--accent);background:var(--plane)}}.learning-question small{{display:block;color:var(--accent-ink);font-weight:800}}.learning-question strong{{display:block;margin-top:3px;font-family:"Songti SC","SimSun",serif;font-size:20px;line-height:1.55}}.section-label{{display:block;margin-bottom:8px;color:var(--accent-ink);font-size:11px;font-weight:900;letter-spacing:.1em}}.author-case,.reconstruction,.reader-explanation,.takeaway,.direct-apply{{margin:20px 0;padding:20px 0;border-top:1px solid var(--line)}}.author-case h3,.reconstruction h3,.reader-explanation h3,.takeaway h3,.direct-apply h3{{margin:0 0 8px;font-size:19px}}.author-case blockquote{{margin:9px 0;font-family:"Songti SC","SimSun",serif;font-size:19px;font-weight:700;white-space:pre-wrap}}.case-meta{{margin:7px 0 0;color:var(--muted);font-size:12px}}.reconstruction-grid{{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:24px}}.reconstruction ol{{margin:5px 0;padding-left:22px}}.reconstruction li{{padding:4px 0}}.takeaway,.direct-apply{{padding:20px;background:var(--plane)}}.pattern{{margin:12px 0 0;padding:12px 14px;border:1px solid var(--line);background:var(--white);color:var(--accent-ink);font-weight:800}}.observation{{margin:20px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);background:var(--plane)}}.observation summary{{padding:16px 20px;cursor:pointer;color:var(--accent-ink);font-weight:900}}.observation-grid{{display:grid;grid-template-columns:1fr 1fr;gap:1px;padding:0 20px 20px}}.observation-grid>div{{padding:15px;background:var(--white)}}.observation-grid b{{display:block;margin-bottom:5px}}.observation-grid ul{{margin:0;padding-left:20px}}.evidence-drawer{{margin-top:24px;border-top:1px solid var(--line)}}.evidence-drawer summary{{padding:15px 0 4px;cursor:pointer;color:var(--accent-ink);font-weight:800}}.evidence-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:12px}}.evidence-frame{{margin:0;padding:10px;border:1px solid var(--line);background:var(--plane)}}.evidence-frame img{{display:block;width:100%;max-height:340px;object-fit:contain;border-radius:2px;background:#262626}}.evidence-frame figcaption{{margin-top:8px;color:var(--muted);font-size:12px}}.course-footer{{padding:30px 24px;text-align:center;color:var(--muted);font-size:12px}}:focus-visible{{outline:2px solid var(--accent-ink);outline-offset:3px}}
.expression-sequence{{position:relative;margin:28px 0 22px;padding-left:32px}}.expression-sequence::before{{content:"";position:absolute;top:10px;bottom:14px;left:8px;width:1px;background:var(--line)}}.expression-step{{position:relative;margin:0 0 26px}}.expression-step:last-child{{margin-bottom:0}}.expression-step::before{{content:"";position:absolute;z-index:1;top:7px;left:-28px;width:9px;height:9px;border:1px solid var(--accent);border-radius:50%;background:var(--paper)}}.expression-step[data-step="author"]::before{{background:var(--accent)}}.author-statement,.plain-rewrite,.ai-advice{{margin:0;padding:0}}.author-statement blockquote{{margin:7px 0 0;font-family:"Songti SC","SimSun",serif;font-size:clamp(19px,2.2vw,23px);font-weight:700;line-height:1.75}}.plain-rewrite h3,.ai-advice h3{{margin:0;font-size:18px}}.plain-rewrite p,.ai-advice p{{margin:7px 0 0}}.ai-advice{{padding:18px 20px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);background:var(--plane)}}.ai-advice ol{{margin:10px 0 0;padding-left:23px}}.ai-advice li{{padding:4px 0}}.verdict-badge{{display:inline-flex;margin-left:8px;padding:2px 7px;border:1px solid var(--accent);border-radius:2px;color:var(--accent-ink);font-size:11px;font-weight:900}}.ai-advice[data-verdict="incorrect"]{{background:var(--danger-plane)}}.ai-advice[data-verdict="incorrect"] .verdict-badge{{border-color:var(--danger);color:var(--danger)}}.ai-advice[data-verdict="partially_correct"],.ai-advice[data-verdict="insufficient_evidence"]{{background:var(--caution-plane)}}.ai-advice[data-verdict="partially_correct"] .verdict-badge,.ai-advice[data-verdict="insufficient_evidence"] .verdict-badge{{border-color:var(--caution);color:var(--caution)}}.adaptive-summary{{margin:24px 0;padding:16px 0;border-top:1px dotted var(--line);border-bottom:1px dotted var(--line);font-family:"Songti SC","SimSun",serif;font-size:17px;font-weight:700}}.source-quotes{{margin:22px 0;padding:20px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}.source-quotes h3,.adaptive-block h3{{margin:0 0 8px;font-size:19px}}.source-quote-line{{margin:8px 0 0;font-family:"Songti SC","SimSun",serif;font-size:18px;font-weight:700;line-height:1.9}}.source-quote-item{{display:inline}}.source-quote-separator{{color:var(--accent);font-weight:400}}.adaptive-block{{margin:0;padding:24px 0;border-top:1px solid var(--line)}}.adaptive-block ul,.adaptive-block ol{{margin:7px 0 0;padding-left:23px}}.adaptive-block li{{padding:4px 0}}.block-takeaway,.block-application,.block-limitations{{margin:16px 0;padding:22px;background:var(--plane);border-top-color:var(--accent)}}.block-limitations{{background:var(--caution-plane)}}.block-summary{{margin-top:16px;padding:22px;border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);background:var(--white)}}.adaptive-comparison{{overflow-x:auto}}.adaptive-block table{{width:100%;border-collapse:collapse}}.adaptive-block th,.adaptive-block td{{padding:10px;border:1px solid var(--line);text-align:left;vertical-align:top}}.adaptive-block th{{background:var(--plane)}}.case-reconstruction-grid{{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:24px}}.adaptive-observation{{margin:16px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);background:var(--plane)}}.adaptive-observation summary{{padding:16px 20px;cursor:pointer;color:var(--accent-ink);font-weight:900}}
@media(max-width:920px){{.course-shell{{display:block;max-width:920px;padding:18px 14px 60px}}.course-sidebar{{display:none}}.mobile-course-nav{{display:block}}.course-hero{{padding:38px 34px}}.learning-chapter{{padding:38px 34px}}}}
@media(max-width:620px){{body{{font-size:15px}}.course-shell{{padding:0}}.course-main{{border:0}}.course-hero{{padding:30px 20px}}.learning-chapter{{padding:32px 20px}}.hero-summary ul,.reconstruction-grid,.case-reconstruction-grid,.observation-grid,.evidence-grid{{grid-template-columns:1fr}}.hero-summary ul{{gap:9px}}.chapter-heading{{display:block}}.source-jump{{display:block;margin-top:12px}}.learning-question strong{{font-size:18px}}.expression-sequence{{padding-left:25px}}.expression-sequence::before{{left:6px}}.expression-step::before{{left:-23px}}.adaptive-block{{padding:21px 0}}.block-takeaway,.block-application,.block-limitations,.block-summary{{padding:18px}}.adaptive-comparison{{overflow:visible}}.adaptive-comparison table,.adaptive-comparison tbody,.adaptive-comparison tr,.adaptive-comparison th,.adaptive-comparison td{{display:block;width:100%}}.adaptive-comparison thead{{display:none}}.adaptive-comparison tr{{padding:10px 0;border-top:1px solid var(--line)}}.adaptive-comparison th,.adaptive-comparison td{{display:grid;grid-template-columns:70px minmax(0,1fr);gap:10px;padding:7px 0;border:0;border-bottom:1px dotted var(--line);background:transparent}}.adaptive-comparison th::before,.adaptive-comparison td::before{{content:attr(data-label);color:var(--muted);font-size:12px;font-weight:700}}}}
@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}#reading-progress{{transition:none}}}}
</style>
</head>
<body>
<div class="reading-track" aria-hidden="true"><div id="reading-progress"></div></div>
<div class="course-shell">
<aside class="course-sidebar" aria-label="课程章节目录">
<div class="brand-kicker">OFFLINE LEARNING NOTE</div>
<h2>{escape(title)}</h2>
<p>{chapter_count} 章 · 当前章节会自动高亮</p>
<nav>{nav_items}</nav>
</aside>
<main class="course-main">
<header class="course-hero">
  <div class="eyebrow">{hero_kicker}</div>
<h1>{escape(title)}</h1>
<div class="hero-meta">作者：{author} · 共 {chapter_count} 章 · 完全离线阅读</div>
<div class="hero-summary"><b>读完你将能够</b><ul>{outcome_items}</ul></div>
</header>
<details class="mobile-course-nav"><summary>展开 {chapter_count} 章目录</summary><nav class="mobile-course-links">{mobile_items}</nav></details>
{cards}
  <footer class="course-footer">{footer_text}</footer>
</main>
</div>
<script>
(() => {{
  const progress = document.getElementById("reading-progress");
  const chapters = [...document.querySelectorAll(".learning-chapter")];
  const links = [...document.querySelectorAll(".course-nav-link")];
  const updateProgress = () => {{
    const max = document.documentElement.scrollHeight - innerHeight;
    const ratio = max > 0 ? Math.min(1, scrollY / max) : 1;
    progress.style.transform = `scaleX(${{ratio}})`;
  }};
  const observer = new IntersectionObserver((entries) => {{
    const visible = entries.filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    links.forEach((link) => {{
      const current = link.dataset.chapterLink === visible.target.id;
      if (current) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    }});
  }}, {{rootMargin:"-20% 0px -65% 0px", threshold:[0,.2,.6]}});
  chapters.forEach((chapter) => observer.observe(chapter));
  addEventListener("scroll", updateProgress, {{passive:true}});
  addEventListener("resize", updateProgress);
  updateProgress();
}})();
</script>
</body>
</html>'''


def _render_adaptive_chapter(
    chapter: dict[str, Any],
    source_url: str,
    stage_info: tuple[int, dict[str, Any]] | None,
    ai_advice_enabled: bool | None = None,
) -> str:
    chapter_id = escape(str(chapter.get("chapter_id", "")))
    chapter_number = escape(str(chapter.get("chapter_index", "")))
    timestamp = _chapter_timestamp(chapter)
    stage_label = (
        f'阶段 {stage_info[0]} · {stage_info[1].get("title", "")}'
        if stage_info
        else "独立章节"
    )
    role = str(chapter.get("chapter_role") or "")
    role_label = escape(ADAPTIVE_ROLE_LABELS.get(role, role or "章节"))
    if ai_advice_enabled is None:
        expression = (
            f'<p class="adaptive-summary">{escape(str(chapter.get("chapter_summary", "")))}</p>'
            + _render_source_quotes(chapter.get("source_quotes"), source_url, timestamp)
        )
    else:
        expression_steps = (
            _render_expression_step(
                "author",
                _render_author_statement(chapter.get("author_statement")),
            )
            + _render_expression_step(
                "rewrite",
                _render_plain_rewrite(chapter.get("plain_rewrite")),
            )
            + _render_expression_step(
                "advice",
                _render_ai_advice(chapter.get("ai_advice"))
                if ai_advice_enabled
                else "",
            )
        )
        expression = (
            '<div class="expression-sequence" aria-label="作者观点理解流程">'
            f"{expression_steps}</div>"
            f'<p class="adaptive-summary">{escape(str(chapter.get("chapter_summary", "")))}</p>'
        )
    blocks = "".join(
        _render_adaptive_block(block)
        for block in chapter.get("content_blocks", [])
        if isinstance(block, dict)
    )
    evidence = _render_learning_evidence(chapter.get("evidence"), source_url)
    return f'''<article class="learning-chapter" id="{chapter_id}" data-chapter-role="{escape(role)}">
<header class="chapter-heading">
<div><span class="chapter-index">第 {chapter_number} 章</span><span class="role-badge">{role_label}</span><span class="stage-label">{escape(stage_label)}</span><h2>{escape(str(chapter.get("title", "")))}</h2></div>
<span class="source-jump">{_video_link(source_url, timestamp, "回到原片 " + timestamp)}</span>
</header>
{expression}
{blocks}
{evidence}
</article>'''


def _render_expression_step(step: str, content: str) -> str:
    if not content:
        return ""
    return (
        f'<div class="expression-step" data-step="{escape(step)}">'
        f"{content}</div>"
    )


def _render_author_statement(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return (
        '<section class="author-statement">'
        '<span class="section-label">作者原话</span>'
        f"<blockquote>“{escape(text)}”</blockquote>"
        "</section>"
    )


def _render_plain_rewrite(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return (
        '<section class="plain-rewrite">'
        '<span class="section-label">通俗改写</span>'
        "<h3>换成大白话怎么理解</h3>"
        f"<p>{escape(text)}</p>"
        "</section>"
    )


def _render_ai_advice(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    verdict = str(value.get("verdict") or "")
    label = AI_ADVICE_VERDICT_LABELS.get(verdict, "需要复核")
    guidance = "".join(
        f"<li>{escape(str(item))}</li>"
        for item in value.get("guidance", [])
        if str(item).strip()
    )
    return (
        f'<section class="ai-advice" data-verdict="{escape(verdict)}">'
        '<span class="section-label">AI 建议</span>'
        f'<h3>正确性判断<span class="verdict-badge">{escape(label)}</span></h3>'
        f'<p>{escape(str(value.get("analysis") or ""))}</p>'
        f"<ol>{guidance}</ol>"
        "</section>"
    )


def _render_source_quotes(value: Any, source_url: str, fallback_timestamp: str) -> str:
    if not isinstance(value, list) or not value:
        return ""
    quotes = []
    for item in value:
        if not isinstance(item, dict):
            continue
        quotes.append(
            '<span class="source-quote-item">'
            f'“{escape(str(item.get("text", "")))}”'
            "</span>"
        )
    if not quotes:
        return ""
    return (
        '<section class="source-quotes"><span class="section-label">作者原话</span>'
        '<h3>先看作者实际说了什么</h3>'
        '<blockquote class="source-quote-line">'
        + '<span class="source-quote-separator">；</span>'.join(quotes)
        + "。</blockquote>"
        + "</section>"
    )


def _render_adaptive_block(block: dict[str, Any]) -> str:
    block_type = str(block.get("type") or "")
    title = escape(str(block.get("title") or ""))
    label = {
        "scope_facts": "事实范围",
        "case_reconstruction": "案例复原",
        "explanation": "理解说明",
        "process": "过程步骤",
        "comparison": "对比判断",
        "limitations": "边界限制",
        "takeaway": "方法提炼",
        "application": "迁移应用",
        "observation": "观察重点",
        "summary": "本章结论",
    }.get(block_type, "章节内容")

    if block_type in {"scope_facts", "limitations"}:
        items = "".join(
            f"<li>{escape(str(item))}</li>"
            for item in block.get("items", [])
            if str(item).strip()
        )
        content = f"<ul>{items}</ul>"
    elif block_type in {"explanation", "summary", "application"}:
        content = f'<p>{escape(str(block.get("text", "")))}</p>'
    elif block_type == "takeaway":
        pattern = str(block.get("pattern") or "").strip()
        pattern_html = (
            f'<div class="pattern">可复用结构：{escape(pattern)}</div>' if pattern else ""
        )
        content = f'<p>{escape(str(block.get("text", "")))}</p>{pattern_html}'
    elif block_type == "case_reconstruction":
        items = "".join(
            f"<li>{escape(str(item))}</li>"
            for item in block.get("sequence", [])
            if str(item).strip()
        )
        content = (
            '<div class="case-reconstruction-grid"><div><b>案例情境</b>'
            f'<p>{escape(str(block.get("context", "")))}</p><b>最后结果</b>'
            f'<p>{escape(str(block.get("result", "")))}</p></div>'
            f'<div><b>过程顺序</b><ol>{items}</ol></div></div>'
        )
    elif block_type == "process":
        items = "".join(
            f"<li>{escape(str(item))}</li>"
            for item in block.get("steps", [])
            if str(item).strip()
        )
        content = f"<ol>{items}</ol>"
    elif block_type == "comparison":
        rows = []
        for row in block.get("rows", []):
            if not isinstance(row, dict):
                continue
            label_text = row.get("label") or row.get("option") or ""
            detail = row.get("detail") or ""
            avoid = row.get("avoid") or ""
            recommend = row.get("recommend") or ""
            rows.append(
                "<tr>"
                f'<th data-label="选项">{escape(str(label_text))}</th>'
                f'<td data-label="说明">{escape(str(detail))}</td>'
                f'<td data-label="避免">{escape(str(avoid))}</td>'
                f'<td data-label="建议">{escape(str(recommend))}</td>'
                "</tr>"
            )
        content = (
            '<div class="adaptive-comparison"><table><thead><tr>'
            "<th>选项</th><th>说明</th><th>避免</th><th>建议</th>"
            f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        )
    elif block_type == "observation":
        common = "".join(
            f"<li>{escape(str(item))}</li>"
            for item in block.get("common_focus", [])
            if str(item).strip()
        )
        resolution = "".join(
            f"<li>{escape(str(item))}</li>"
            for item in block.get("author_resolution", [])
            if str(item).strip()
        )
        content = (
            '<details class="adaptive-observation" open><summary>展开观察重点</summary>'
            '<div class="observation-grid"><div><b>大多数人先注意</b>'
            f"<ul>{common}</ul></div><div><b>作者真正处理</b>"
            f"<ul>{resolution}</ul></div></div></details>"
        )
    else:
        return ""

    return (
        f'<section class="adaptive-block block-{escape(block_type)}">'
        f'<span class="section-label">{escape(label)}</span><h3>{title}</h3>'
        f"{content}</section>"
    )


def _render_learning_chapter(
    chapter: dict[str, Any],
    source_url: str,
    stage_info: tuple[int, dict[str, Any]] | None,
) -> str:
    chapter_id = escape(str(chapter.get("chapter_id", "")))
    chapter_number = escape(str(chapter.get("chapter_index", "")))
    timestamp = _chapter_timestamp(chapter)
    stage_label = (
        f'阶段 {stage_info[0]} · {stage_info[1].get("title", "")}'
        if stage_info
        else "独立章节"
    )
    reconstruction = chapter.get("case_reconstruction")
    if not isinstance(reconstruction, dict):
        reconstruction = {}
    sequence = "".join(
        f"<li>{escape(str(item))}</li>"
        for item in reconstruction.get("sequence", [])
        if str(item).strip()
    )
    observation = _render_learning_observation(chapter.get("observation"))
    author_examples = _render_learning_author_examples(chapter, source_url, timestamp)
    evidence = _render_learning_evidence(chapter.get("evidence"), source_url)
    return f'''<article class="learning-chapter" id="{chapter_id}">
<header class="chapter-heading">
<div><span class="chapter-index">第 {chapter_number} 章</span><span class="stage-label">{escape(stage_label)}</span><h2>{escape(str(chapter.get("title", "")))}</h2></div>
<span class="source-jump">{_video_link(source_url, timestamp, "回到原片 " + timestamp)}</span>
</header>
<section class="learning-question"><small>本章要解决的问题</small><strong>{escape(str(chapter.get("learning_question", "")))}</strong></section>
{author_examples}
<section class="reconstruction"><span class="section-label">复原作者原例</span><h3>作者怎么做</h3><div class="reconstruction-grid"><div><b>案例情境</b><p>{escape(str(reconstruction.get("context", "")))}</p><b>最后结果</b><p>{escape(str(reconstruction.get("result", "")))}</p></div><div><b>过程顺序</b><ol>{sequence}</ol></div></div></section>
<section class="reader-explanation"><span class="section-label">读懂因果</span><h3>为什么有效</h3><p>{escape(str(chapter.get("reader_explanation", "")))}</p></section>
<section class="takeaway"><span class="section-label">方法提炼</span><h3>真正精髓</h3><p>{escape(str(chapter.get("core_takeaway", "")))}</p><div class="pattern">可复用结构：{escape(str(chapter.get("reusable_pattern", "")))}</div></section>
<section class="direct-apply"><span class="section-label">迁移应用</span><h3>直接套用</h3><p>{escape(str(chapter.get("direct_application", "")))}</p></section>
{observation}
{evidence}
</article>'''


def _render_learning_author_examples(
    chapter: dict[str, Any],
    source_url: str,
    fallback_timestamp: str,
) -> str:
    blocks = []
    for item in chapter.get("author_examples", []):
        if not isinstance(item, dict):
            continue
        timestamp = str(item.get("timestamp") or fallback_timestamp)
        blocks.append(
            '<section class="author-case">'
            '<span class="section-label">视频中的具体案例</span>'
            f'<h3>{escape(str(item.get("label") or "作者原例"))}</h3>'
            f'<blockquote>{escape(str(item.get("text", "")))}</blockquote>'
            f'<p class="case-meta">{escape(str(item.get("completeness", "")))} · '
            f'{_video_link(source_url, timestamp, "回看原例 " + timestamp)}</p>'
            "</section>"
        )
    return "".join(blocks)


def _render_learning_observation(value: Any) -> str:
    if not isinstance(value, dict) or value.get("enabled") is not True:
        return ""
    common = "".join(
        f"<li>{escape(str(item))}</li>"
        for item in value.get("common_focus", [])
        if str(item).strip()
    )
    resolution = "".join(
        f"<li>{escape(str(item))}</li>"
        for item in value.get("author_resolution", [])
        if str(item).strip()
    )
    return (
        '<details class="observation" data-observation="static-reveal">'
        "<summary>展开观察重点：表面上看见了什么，作者真正处理了什么</summary>"
        '<div class="observation-grid"><div><b>大多数人先注意</b>'
        f"<ul>{common}</ul></div><div><b>作者真正处理</b>"
        f"<ul>{resolution}</ul></div></div></details>"
    )


def _render_learning_evidence(value: Any, source_url: str) -> str:
    if not isinstance(value, list) or not value:
        return ""
    figures = []
    for item in value:
        if not isinstance(item, dict):
            continue
        timestamp = str(item.get("timestamp", ""))
        proves = str(item.get("proves") or "视频关键画面")
        figures.append(
            '<figure class="evidence-frame">'
            f'<img src="{escape(str(item.get("frame_src", "")))}" '
            f'alt="{escape(proves)}" loading="lazy" decoding="async">'
            f'<figcaption>{_video_link(source_url, timestamp, "视频时间戳 " + timestamp)}'
            f" · {escape(proves)}</figcaption></figure>"
        )
    if not figures:
        return ""
    return (
        '<details class="evidence-drawer"><summary>展开视频证据与关键截图</summary>'
        f'<div class="evidence-grid">{"".join(figures)}</div></details>'
    )


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
