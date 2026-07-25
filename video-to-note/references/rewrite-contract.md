# 动态视频笔记重写契约

把 `evidence_pack.json` 与 schema v3 骨架重写为可离线渲染的笔记 JSON。只输出 JSON。

## 新任务版本

```json
{
  "schema_version": 3,
  "learning_design_version": "adaptive-blocks-v1",
  "ai_advice_enabled": true
}
```

旧数据没有 `learning_design_version` 时继续使用旧渲染器；已有 `b-c-v1` 仍兼容。
新任务的 `ai_advice_enabled` 默认开启，用户可以关闭。

## 总原则

1. 按话题、案例、操作目标和结论的语义边界切章，最多 40 章。
2. 连续教程保持作者原顺序；重复、闲聊和转场不单独成章。
3. 每句话必须增加新信息，相同背景和结论只写一次。
4. 页面中的作者原话只保留一句核心原意；内部 `source_quotes` 继续保留逐字证据和时间戳。
5. 通俗改写只优化表达，AI 建议独立负责正确性判断和修正指导。
6. 不生成举一反三案例，不把 AI 判断伪装成作者观点。
7. 不生成答题、评分、答案输入、学习记录或 GPT 评价字段。

## 每章必填字段

```json
{
  "chapter_role": "overview",
  "chapter_summary": "本章的一句白话定位",
  "author_statement": "作者核心原意的一句话整理",
  "plain_rewrite": "通顺、易懂且不偷换观点的大白话解释",
  "source_quotes": [
    {
      "text": "能在转写中逐字定位的作者原话",
      "timestamp": "00:00:42"
    }
  ],
  "content_blocks": [],
  "evidence": [
    {
      "timestamp": "00:00:42",
      "frame_src": "./frames/example.jpg",
      "proves": "该画面证明的具体事实"
    }
  ],
  "ai_advice": {
    "verdict": "correct",
    "analysis": "对作者观点正确性的简短判断。",
    "guidance": ["必要且可执行的建议"]
  }
}
```

`chapter_role` 只能是 `overview`、`method`、`decision`、`process`、`case`、
`warning` 或 `conclusion`。

`ai_advice_enabled` 为 `true` 时必须生成 `ai_advice`；为 `false` 时必须省略
`ai_advice`，避免无效输出 Token。

`ai_advice.verdict` 只能是：

- `correct`
- `partially_correct`
- `incorrect`
- `insufficient_evidence`

## 内容块

按需要组合，不按固定骨架补齐：

### 范围事实

```json
{"type":"scope_facts","title":"作者实际做到了什么程度","items":["具体事实"]}
```

### 案例复原

```json
{
  "type": "case_reconstruction",
  "title": "作者案例",
  "context": "案例情境",
  "sequence": ["作者真实步骤"],
  "result": "视频中出现的结果"
}
```

只有情境、过程和结果构成完整案例时才使用。

### 解释、结论与迁移

```json
{"type":"explanation","title":"为什么这样做","text":"因果解释"}
{"type":"summary","title":"最后总结","text":"本章结论"}
{"type":"takeaway","title":"方法提炼","text":"一个主结论","pattern":"可选结构"}
{"type":"application","title":"迁移应用","text":"明确迁移步骤"}
```

没有明确迁移步骤时省略 `application`。概览、背景、观点和结论章节通常不应输出迁移块。

### 过程、限制、观察和比较

```json
{"type":"process","title":"作者怎么做","steps":["步骤"]}
{"type":"limitations","title":"当前边界","items":["限制"]}
{
  "type":"observation",
  "title":"观察重点",
  "common_focus":["表面现象"],
  "author_resolution":["作者真正处理的内容"]
}
{
  "type":"comparison",
  "title":"方案取舍",
  "rows":[{"label":"方案","detail":"说明","avoid":"避免","recommend":"建议"}]
}
```

`observation` 是静态揭示，不包含问题答案、选择项、输入框或评分。

## 作者原话、通俗改写与 AI 建议门禁

- `author_statement` 必须只有一句，允许修正口语和语病，但不得改变作者立场或补造事实。
- `plain_rewrite` 必须比作者原话更通俗顺畅，但不能代替 AI 建议进行隐性事实纠错。
- `source_quotes[].text` 必须来自当前章节覆盖的转写片段，保留原有数量词和限定词。
- 禁止把多段字幕拼成作者从未连续说过的一句话。
- 页面中的一句作者原话写入 `author_statement`；不得用概括替代内部 `source_quotes` 中的逐字作者原话。
- AI 建议必须先给出正确性判断，再给出依据与指导；证据不足时明确标注，不能编造确定结论。
- 正确观点使用短建议；错误、遗漏或高风险误导才展开详细方案。
- 原话、标题、内容块、截图和时间戳必须语义一致。
- 无法找到原话或证据时停止该章重写并标记待人工复核，不得猜测。

作者原话、通俗改写和 AI 建议必须在同一次结构化重写中按开关生成。只输入当前章节的
语义片段和证据，不得为了 AI 建议再次加载完整字幕。

## 证据与切章

最终章节如果不同于 `evidence_pack.json` 的候选章节，必须重新按最终时间范围映射转写片段和截图。
每章至少一个 `evidence`；截图只证明画面确实呈现的事实，不代替作者原话。

## 旧版字段兼容

旧 `b-c-v1` 文件可能包含以下字段，验证器与渲染器继续支持，但新任务不生成：

- `learning_question`
- `author_examples`
- `case_reconstruction`
- `reader_explanation`
- `core_takeaway`
- `reusable_pattern`
- `direct_application`
- `observation`
- `common_focus`
- `author_resolution`
- `boundary_note`

## 其他通用字段

- `learning_design_version`：顶层版本。
- `citations`：只引用顶层已存在的资料来源。
- `diagram_spec`：只有图表显著提升理解时才输出，由本地脚本绘制。
- `action_items`：只有视频明确提出负责人、任务或时间要求时才输出。
