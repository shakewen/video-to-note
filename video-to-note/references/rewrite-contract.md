# 动态视频笔记重写契约

把 `evidence_pack.json` 与 schema v3 骨架重写为可离线渲染的笔记 JSON。只输出 JSON。

## 总原则

1. 按任务目标、工具页面和结果节点自然切章，通常 5～12 章，最多 12 章。
2. 连续教程保持作者原顺序；重复、闲聊和转场不单独成章。
3. 每句话必须增加新信息。相同环境、背景和结论只写一次。
4. 保留作者真实操作、参数、提示词、案例和时间戳；不生成举一反三案例。
5. AI 补充只能用于新手解释，并标记 `source_kind: ai_teaching`。
6. 不输出原始 SVG 或 Mermaid。只输出精简 `diagram_spec`，由本地脚本绘图。

## 动态模板路由

- `sop`：软件、网页、控制台或实物操作。
- `concept`：术语、原理、因果关系。
- `matrix`：方案、参数、优缺点或选择判断。
- `brief`：必要转场或作者观点；禁止图表和表格。

每章只选一种 `template_type`，不要为了凑样式改变视频事实。

## 通用字段

- `chapter_summary`：一句白话重点。
- `key_points`：只保留本章不同的关键事实，数量随内容变化。
- `author_examples`：仅记录视频中真实出现的案例，含时间戳和完整度说明。
- `evidence`：时间戳、相对截图路径、截图证明的事实。
- `citations`：只引用顶层已存在的资料来源。

## A：操作 SOP

- `operation_environment`：按“软件或网页 → 功能模块 → 工具或入口”说明位置；视频未展示时写“原视频未明确展示，待人工确认”。
- `source_operations`：每步包含 `location`、`action`、`parameter_or_result`、`text`、`source_kind: video_source`。
- 步骤数量按作者实际操作动态生成。
- 保留必要的 `prerequisites`、`tips`、`verification` 和 `troubleshooting`。

## B：深度概念

- `decision_rules`：作者讲明的判断或因果规则。
- 只有出现复杂术语时才生成 `feynman_scaffolding`，字段为 `term`、`definition`、`metaphor`、`misconception`。
- 费曼解释属于 AI 通俗解释，不得伪装成作者原话。

## C：对比决策

- `tradeoff`：一句话说明核心取舍。
- `decision_matrix`：动态行列表，每行包含 `option`、`avoid`、`recommend`。

## D：极简速报

- 只保留一句白话和可选的 `speaker_attitude`。
- 不生成 `diagram_spec`、截图表格或行动项。

## 图表语义

- 流程：`{"type":"flow","nodes":[...],"links":[[起点,终点]]}`
- 关系：`{"type":"radial","center":"核心词","branches":[...]}`
- 对比：`{"type":"matrix","x_label":"横轴","y_label":"纵轴","points":[{"label":"方案","x":0-100,"y":0-100}]}`
- 不需要图表：省略 `diagram_spec`。

节点、关系和标签必须来自本章真实内容。

## 行动项

只有视频明确提出负责人、任务或时间要求时才输出顶层 `action_items`。每项包含 `who`、`what`、`when`、`note`；没有明确行动项时直接省略，禁止批量填写“待人工确认”。
