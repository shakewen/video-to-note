from __future__ import annotations

import copy
import ctypes
import hashlib
import re
from html import escape
from typing import Any


TEMPLATE_TYPES = ("sop", "concept", "decision", "brief")
TEMPLATE_ALIASES = {
    "操作sop": "sop",
    "操作sop流": "sop",
    "深度解构": "concept",
    "深度概念解构": "concept",
    "对比决策": "decision",
    "对比决策矩阵": "decision",
    "极简观点": "brief",
    "极简速报": "brief",
    "极简速报/观点卡": "brief",
}

CLASSIFIER_KEYWORDS = {
    "sop": ("点击", "上传", "导入", "配置", "设置", "控制台", "命令", "节点", "画布", "操作", "步骤", "剪辑", "调色", "生成", "参数", "安装"),
    "concept": ("为什么", "原理", "本质", "机制", "因果", "逻辑", "关系", "连续", "认知", "声音", "构图", "思维", "解释"),
    "decision": ("选择", "对比", "区别", "权衡", "成本", "质量", "优缺点", "版本", "自由度", "风险", "审核", "控制", "取舍", "还是"),
    "brief": ("结尾", "总结", "感谢", "下期", "态度", "想说", "收束", "结束", "开场"),
}


def to_simplified(text: str) -> str:
    """Convert Chinese text with the Windows locale service, with a tiny fallback."""
    if not text:
        return text
    try:
        mapper = ctypes.windll.kernel32.LCMapStringEx
        size = mapper("zh-CN", 0x02000000, text, len(text), None, 0, None, None, 0)
        if size:
            buffer = ctypes.create_unicode_buffer(size)
            mapper("zh-CN", 0x02000000, text, len(text), buffer, size, None, None, 0)
            return _localize_mainland_terms(buffer.value)
    except (AttributeError, OSError):
        pass
    table = str.maketrans("與為這個學會開關後裡資訊品質畫聲體從", "与为这个学会开关后里信息质量画声体从")
    return _localize_mainland_terms(text.translate(table))


def _localize_mainland_terms(text: str) -> str:
    replacements = {
        "影片": "视频",
        "资讯": "信息",
        "品质": "质量",
        "使用者": "用户",
        "介面": "界面",
        "软体": "软件",
        "萤幕": "屏幕",
        "什麽": "什么",
        "怎麽": "怎么",
        "於": "于",
        "後": "后",
        "乾净": "干净",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def classify_chapter(chapter: dict[str, Any]) -> str:
    explicit = str(chapter.get("template_type", "")).strip().lower().strip("[]【】")
    if explicit in TEMPLATE_TYPES:
        return explicit
    if explicit in TEMPLATE_ALIASES:
        return TEMPLATE_ALIASES[explicit]

    text = " ".join(
        [str(chapter.get("title", ""))]
        + [str(item) for item in chapter.get("body", [])]
        + [str(item) for item in chapter.get("detail_restoration", [])]
    ).lower()
    scores = {
        kind: sum(3 if keyword in str(chapter.get("title", "")) else 1 for keyword in keywords if keyword.lower() in text)
        for kind, keywords in CLASSIFIER_KEYWORDS.items()
    }
    if max(scores.values(), default=0) == 0:
        diagram_type = str(chapter.get("diagram_type", ""))
        if diagram_type in ("matrix", "decision_tree", "checklist"):
            return "decision"
        if diagram_type in ("causal", "concept"):
            return "concept"
        return "sop"
    priority = {"brief": 0, "concept": 1, "decision": 2, "sop": 3}
    return max(scores, key=lambda key: (scores[key], -priority[key]))


def prepare_cognitive_chapters(
    chapters: list[dict[str, Any]],
    overrides: dict[int | str, str] | None = None,
) -> list[dict[str, Any]]:
    overrides = overrides or {}
    prepared = []
    for index, source in enumerate(chapters, 1):
        item = _simplify_structure(copy.deepcopy(source))
        item["title"] = re.sub(r"^\s*\d+\.\s*", "", str(item.get("title", "")))
        override = overrides.get(index, overrides.get(str(index)))
        if override:
            item["template_type"] = override
        template_type = classify_chapter(item)
        item["template_type"] = template_type
        item["chapter_index"] = int(item.get("chapter_index") or index)
        body = [_strip_rctf(str(line)) for line in item.get("body", [])]
        details = [str(line) for line in item.get("detail_restoration", [])]
        if not details:
            details = body[:]
        item["plain_summary"] = str(item.get("plain_summary") or (body[-1] if body else item.get("title", "")))
        item["template_data"] = _build_template_data(item, template_type, body, details)
        item["detail_restoration"] = details
        if not item.get("visual_anchor"):
            timestamp = str((item.get("frame") or {}).get("timestamp", "")).strip()
            item["visual_anchor"] = f"{timestamp} 对应本章真实画面。" if timestamp else "本章以原视频时间戳作为事实锚点。"
        if template_type == "brief":
            item["diagram_type"] = "none"
            item["svg"] = ""
        else:
            item["diagram_type"] = {"sop": "flow", "concept": "concept", "decision": "matrix"}[template_type]
            item["svg"] = _build_svg(item, index)
        prepared.append(item)
    return prepared


def _simplify_structure(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {name: _simplify_structure(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [_simplify_structure(item, key) for item in value]
    if isinstance(value, str) and key not in {"src", "source_url", "url", "svg"}:
        return to_simplified(value)
    return value


def _strip_rctf(value: str) -> str:
    return re.sub(r"^(问题|步骤|陷阱|结论)\s*[：:]\s*", "", value).strip()


def _build_template_data(item: dict[str, Any], kind: str, body: list[str], details: list[str]) -> dict[str, Any]:
    supplied = item.get("template_data")
    if isinstance(supplied, dict) and supplied:
        return supplied
    warning = body[2] if len(body) > 2 else (details[-1] if details else "执行前先核对输入与输出。")
    conclusion = body[-1] if body else str(item.get("plain_summary", ""))

    if kind == "sop":
        source_steps = details[:3] or body[:3]
        steps = []
        for number, detail in enumerate(source_steps, 1):
            steps.append({
                "action": _short_label(detail, 10) or f"步骤 {number}",
                "detail": detail,
                "parameters": "、".join(_extract_parameters(detail)) or "按画面与目标确认",
            })
        return {"steps": steps, "warning": warning}

    if kind == "concept":
        scaffold = item.get("feynman_scaffolding") or {}
        metaphor = str(scaffold.get("metaphor") or "把它想成一条前后相接的日常工作链：上一步变化，会直接改变下一步结果。")
        logic = body[1] if len(body) > 1 else conclusion
        branches = [_short_label(line, 9) for line in (details[:4] or body[:4])]
        while len(branches) < 3:
            branches.append(f"影响 {len(branches) + 1}")
        return {"metaphor": metaphor, "logic": logic, "branches": branches[:4]}

    if kind == "decision":
        rows = []
        sources = details[:3] or body[:3]
        for number, detail in enumerate(sources, 1):
            digest = hashlib.sha1(f"{item.get('title')}:{number}:{detail}".encode("utf-8")).digest()
            avoid_options = [
                warning,
                body[0] if body else "不要脱离章节目标只看单一指标。",
                f"不要只记住“{_short_label(detail, 10)}”而忽略适用条件。",
            ]
            rows.append({
                "option": _short_label(detail, 12) or f"方案 {number}",
                "avoid": avoid_options[(number - 1) % len(avoid_options)],
                "recommend": detail,
                "x": 18 + digest[0] % 65,
                "y": 18 + digest[1] % 65,
            })
        return {"options": rows, "tradeoff": item.get("plain_summary", conclusion)}

    attitude = str(item.get("key_quote") or item.get("quote") or (body[0] if body else conclusion))
    return {"attitude": attitude, "next": conclusion}


def _extract_parameters(text: str) -> list[str]:
    patterns = re.findall(
        r"(?:\b[A-Za-z][A-Za-z0-9._-]*(?:\s+[A-Za-z0-9._-]+){0,2}\b|\b\d+(?:\.\d+)?(?:p|%|秒|分钟|Hz|kHz|倍)?\b|\b\d{1,2}:\d{1,2}\b)",
        text,
    )
    result = []
    for value in patterns:
        value = value.strip()
        if value and value not in result:
            result.append(value)
    return result[:5]


def _short_label(text: str, limit: int) -> str:
    cleaned = re.sub(r"[，。；：、,.!?！？]", " ", text).strip()
    first = cleaned.split()[0] if cleaned else ""
    return first[:limit]


def _build_svg(item: dict[str, Any], index: int) -> str:
    kind = item["template_type"]
    if kind == "sop":
        return _sop_svg(item, index)
    if kind == "concept":
        return _concept_svg(item, index)
    return _decision_svg(item, index)


def _sop_svg(item: dict[str, Any], index: int) -> str:
    steps = item["template_data"]["steps"][:4]
    marker = f"sop-arrow-{index}"
    widths = [max(128, min(184, 94 + len(step["action"]) * 8)) for step in steps]
    gap = 48
    total = sum(widths) + gap * max(0, len(widths) - 1)
    x = (920 - total) / 2
    parts = []
    for number, (step, width) in enumerate(zip(steps, widths), 1):
        fill = "#e7f2f4" if number % 2 else "#ffffff"
        parts.append(f'<rect x="{x:.0f}" y="84" width="{width}" height="72" rx="7" fill="{fill}" stroke="#256d85" stroke-width="1.8"/>')
        parts.append(f'<text x="{x + width/2:.0f}" y="112" text-anchor="middle" class="svg-kicker">STEP {number}</text>')
        parts.append(f'<text x="{x + width/2:.0f}" y="139" text-anchor="middle" class="svg-label">{escape(step["action"])}</text>')
        if number < len(steps):
            parts.append(f'<line x1="{x + width + 7:.0f}" y1="120" x2="{x + width + gap - 10:.0f}" y2="120" stroke="#256d85" stroke-width="2" marker-end="url(#{marker})"/>')
        x += width + gap
    title = escape(_short_label(str(item.get("title", "操作流程")), 18))
    full_title = escape(str(item.get("title", "操作流程")))
    return f'<svg viewBox="0 0 920 240" role="img" aria-label="{title} 操作流程"><title>{full_title}</title><defs><marker id="{marker}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0L9 4.5L0 9Z" fill="#256d85"/></marker></defs><rect x="1" y="1" width="918" height="238" rx="8" fill="#fbfdfd" stroke="#c8dade"/><text x="34" y="42" class="svg-title">{title}</text>{"".join(parts)}</svg>'


def _concept_svg(item: dict[str, Any], index: int) -> str:
    branches = item["template_data"]["branches"]
    center = escape(_short_label(str(item.get("title", "核心概念")), 12))
    full_title = escape(str(item.get("title", "核心概念")))
    coords = [(176, 76), (744, 76), (154, 250), (766, 250)]
    parts = []
    for number, (label, (base_x, base_y)) in enumerate(zip(branches, coords), 1):
        digest = hashlib.sha1(f"{index}:{label}".encode("utf-8")).digest()
        x = base_x + digest[0] % 31 - 15
        y = base_y + digest[1] % 23 - 11
        parts.append(f'<path d="M460 166 Q{(460+x)//2} {(166+y)//2 - 18} {x} {y}" fill="none" stroke="#256d85" stroke-width="1.8"/>')
        parts.append(f'<circle cx="{x}" cy="{y}" r="52" fill="#ffffff" stroke="#7ea5af" stroke-width="1.6"/>')
        parts.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" class="svg-label">{escape(label)}</text>')
    return f'<svg viewBox="0 0 920 330" role="img" aria-label="{center} 辐射关系图"><title>{full_title}</title><rect x="1" y="1" width="918" height="328" rx="8" fill="#fbfdfd" stroke="#c8dade"/><circle cx="460" cy="166" r="72" fill="#e7f2f4" stroke="#256d85" stroke-width="2.2"/><text x="460" y="171" text-anchor="middle" class="svg-title">{center}</text>{"".join(parts)}</svg>'


def _decision_svg(item: dict[str, Any], index: int) -> str:
    rows = item["template_data"]["options"]
    colors = ("#c8564d", "#256d85", "#7c8f62", "#9a6f3f")
    points = []
    for number, row in enumerate(rows, 1):
        x = 110 + int(row["x"]) * 7
        y = 278 - int(row["y"]) * 2
        points.append(f'<circle cx="{x}" cy="{y}" r="11" fill="{colors[(number-1)%len(colors)]}"/><text x="{x+16}" y="{y+5}" class="svg-small">{escape(row["option"])}</text>')
    title = escape(_short_label(str(item.get("title", "方案权衡")), 18))
    full_title = escape(str(item.get("title", "方案权衡")))
    return f'<svg viewBox="0 0 920 340" role="img" aria-label="{title} 对比矩阵"><title>{full_title}</title><defs><marker id="matrix-arrow-{index}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0L9 4.5L0 9Z" fill="#256d85"/></marker></defs><rect x="1" y="1" width="918" height="338" rx="8" fill="#fbfdfd" stroke="#c8dade"/><text x="34" y="40" class="svg-title">{title}</text><line x1="92" y1="292" x2="838" y2="292" stroke="#256d85" stroke-width="2" marker-end="url(#matrix-arrow-{index})"/><line x1="92" y1="292" x2="92" y2="68" stroke="#256d85" stroke-width="2" marker-end="url(#matrix-arrow-{index})"/><text x="780" y="322" class="svg-small">成本 / 约束 →</text><text x="28" y="92" class="svg-small">收益 / 稳定 ↑</text>{"".join(points)}</svg>'
