# AI Expanded 典藏学习笔记实现计划

> **面向 AI 代理的工作者：** 必需子技能：在当前共享工作区使用 executing-plans 逐任务实现此计划。用户已明确要求不创建隔离 worktree。步骤使用复选框（- [ ]）语法跟踪进度。

**目标：** 在冻结的 source-faithful.md 基础上，生成一份独立、可收藏、可直接学习的 ai-expanded.md；支持自然语言要求和按需联网核查。

**架构：** ai-expanded 是独立二阶段命令，不重新加入 note.mode。新增专用 JSON 骨架、结构校验和 Markdown 写入器。AI 先填充内部重塑规划与核查记录，再生成读者 Markdown；时间戳、截图、来源和核查记录不进入最终笔记。

**技术栈：** Python 标准库、现有 PowerShell 运行器、unittest、Agent Reach（仅由代理在 auto 命中风险或用户明确要求时调用）。

---

## 文件结构

- 创建：video-to-note/scripts/runtime/video_note_pipeline/expanded.py
  - Expanded schema、输入快照、结构校验、内部核查记录和 Markdown 写入。
- 修改：video-to-note/scripts/runtime/video_note_pipeline/cli.py:633-887
  - 新增 prepare-ai-expanded-note、validate-ai-expanded-note、write-ai-expanded-markdown。
- 创建：video-to-note/tests/test_ai_expanded.py
  - Expanded 骨架、输入快照、动态学习单元、审计记录、Markdown、CLI 测试。
- 修改：video-to-note/tests/test_source_import.py:22-45,131-140
  - 防止 expanded 命令改变 source-faithful 的唯一主流水线模式，同时允许 Skill 文档说明独立扩展阶段。
- 创建：video-to-note/references/ai-expanded-contract.md
  - 两次 AI 调用、自然语言要求、最小核查门禁、动态单元与禁止输出项。
- 修改：video-to-note/SKILL.md:14-68
  - 用户明确要求“AI 重塑/扩展/典藏学习笔记”才触发独立阶段。
- 修改：video-to-note/references/workflow.md:80-104
  - 修正 source-faithful 的 ai_advice 默认关闭描述，追加 expanded 阶段。

不修改 config.py、init_request.ps1、assets/video-input.yaml、references/rewrite-contract.md 的 source-faithful 行为；不引入 HTTP 客户端、数据库、前端或 HTML 渲染。

### 任务 1：建立 Expanded 骨架与源文件冻结

**文件：**
- 创建：video-to-note/scripts/runtime/video_note_pipeline/expanded.py
- 创建：video-to-note/tests/test_ai_expanded.py

- [ ] **步骤 1：编写失败测试**

~~~python
def test_prepare_expanded_skeleton_keeps_instruction_and_source_digest(self) -> None:
    source = self._write_source("# 原视频笔记\n\n正文")

    payload = prepare_expanded_skeleton(source, "重点讲实际用法；自动核查")

    self.assertEqual(payload["schema_version"], 1)
    self.assertEqual(payload["request"]["instruction"], "重点讲实际用法；自动核查")
    self.assertEqual(payload["source"]["sha256"], sha256(source.read_bytes()).hexdigest())
    self.assertEqual(payload["units"], [])
    self.assertEqual(payload["audit"]["verification"], [])
~~~

- [ ] **步骤 2：运行测试确认失败**

~~~powershell
. .\task-runtime.ps1
& $env:VIDEO_NOTE_PYTHON .\github-repo\video-to-note\video-to-note\tests\test_ai_expanded.py
~~~

预期：ImportError，因为 expanded.py 与 prepare_expanded_skeleton 尚不存在。

- [ ] **步骤 3：编写最小实现**

~~~python
EXPANDED_SCHEMA_VERSION = 1
UNIT_TYPES = {"concept", "method", "operation", "fact"}
VERIFICATION_STATUSES = {"verified", "unresolved", "not_checked"}

class ExpandedValidationError(ValueError):
    pass

def prepare_expanded_skeleton(source_path: Path, instruction: str = "") -> dict[str, Any]:
    source_text = source_path.read_text(encoding="utf-8-sig").strip()
    if not source_text:
        raise ExpandedValidationError("source-faithful Markdown 不能为空")
    return {
        "schema_version": EXPANDED_SCHEMA_VERSION,
        "source": {
            "path": str(source_path),
            "sha256": sha256(source_path.read_bytes()).hexdigest(),
        },
        "request": {"instruction": instruction.strip()},
        "title": "",
        "thesis": "",
        "units": [],
        "application": [],
        "audit": {"verification": []},
    }
~~~

读取失败、目录路径与空文件都转换为 ExpandedValidationError。

- [ ] **步骤 4：运行测试确认通过**

运行步骤 2 的命令。

预期：骨架测试通过。

- [ ] **步骤 5：先写源文件变更的失败测试**

~~~python
def test_validate_expanded_payload_rejects_changed_source(self) -> None:
    payload = prepare_expanded_skeleton(self.source, "")
    self.source.write_text("# 被修改", encoding="utf-8")

    with self.assertRaisesRegex(ExpandedValidationError, "source-faithful 已变化"):
        validate_expanded_payload(payload, self.source)
~~~

- [ ] **步骤 6：实现 SHA-256 防护并回归**

在 validate_expanded_payload 中重新计算 source_path 字节哈希，和 payload["source"]["sha256"] 不一致时抛出上述错误；不得写入或恢复源文件。运行步骤 2 的命令，预期两个测试通过。

### 任务 2：定义动态单元与内部核查记录

**文件：**
- 修改：video-to-note/scripts/runtime/video_note_pipeline/expanded.py
- 修改：video-to-note/tests/test_ai_expanded.py

- [ ] **步骤 1：编写失败的单元测试**

~~~python
def test_validate_expanded_payload_accepts_dynamic_units(self) -> None:
    payload = self._complete_payload()
    payload["units"] = [
        {"type": "concept", "title": "和弦功能", "core": "它决定听感走向", "plain": "把它看成音乐里的角色分工。"},
        {"type": "operation", "title": "输入根音", "goal": "建立和弦骨架", "steps": ["新建轨道", "输入根音"], "checkpoints": ["根音与调性一致"]},
    ]

    result = validate_expanded_payload(payload, self.source)

    self.assertEqual(result["unit_count"], 2)

def test_validate_expanded_payload_rejects_duplicate_titles(self) -> None:
    payload = self._complete_payload()
    payload["units"] = [
        {"type": "concept", "title": "重复", "core": "a", "plain": "b"},
        {"type": "concept", "title": "重复", "core": "c", "plain": "d"},
    ]

    with self.assertRaisesRegex(ExpandedValidationError, "title 重复"):
        validate_expanded_payload(payload, self.source)
~~~

- [ ] **步骤 2：运行测试确认失败**

运行任务 1 的测试命令。

预期：失败，因为 validator 尚未校验 units。

- [ ] **步骤 3：实现按类型的最小校验**

~~~python
def _validate_unit(unit: dict[str, Any], context: str) -> None:
    unit_type = _require_text(unit, "type", context)
    if unit_type not in UNIT_TYPES:
        raise ExpandedValidationError(f"{context}.type 不合法")
    _require_text(unit, "title", context)
    if unit_type == "concept":
        _require_text(unit, "core", context)
        _require_text(unit, "plain", context)
    elif unit_type == "method":
        _require_text(unit, "use_when", context)
        _require_text(unit, "decision_logic", context)
        _require_string_list(unit, "workflow", context, nonempty=True)
    elif unit_type == "operation":
        _require_text(unit, "goal", context)
        _require_string_list(unit, "steps", context, nonempty=True)
        _require_string_list(unit, "checkpoints", context, nonempty=True)
    else:
        _require_text(unit, "conclusion", context)
~~~

仅允许当前类型的必填字段和可选字段 example、boundary、pitfall、comparison、memory_cue；先计算未知字段集合，非空时抛出 ExpandedValidationError。这样禁止增加时间戳、URL 与 source_ref 字段。

- [ ] **步骤 4：编写失败的内部核查记录测试**

~~~python
def test_validation_allows_internal_verification(self) -> None:
    payload = self._complete_payload()
    payload["audit"]["verification"] = [{
        "topic": "某软件版本行为",
        "reason": "auto",
        "status": "verified",
        "reference_urls": ["https://example.com/docs"],
    }]

    validate_expanded_payload(payload, self.source)
~~~

另加 status="certain" 的失败测试，预期错误包含 status 不合法。

- [ ] **步骤 5：实现内部核查记录和最少练习限制**

~~~python
def _validate_verification(item: dict[str, Any], context: str) -> None:
    _require_text(item, "topic", context)
    if item.get("reason") not in {"auto", "targeted"}:
        raise ExpandedValidationError(f"{context}.reason 不合法")
    status = item.get("status")
    if status not in VERIFICATION_STATUSES:
        raise ExpandedValidationError(f"{context}.status 不合法")
    urls = _require_string_list(item, "reference_urls", context)
    if status == "verified" and not urls:
        raise ExpandedValidationError(f"{context}.verified 必须保留来源")
~~~

application 必须是字符串列表，最多 3 项，允许为空。运行 expanded 测试，预期全部通过。

### 任务 3：写入无审计痕迹的 Markdown

**文件：**
- 修改：video-to-note/scripts/runtime/video_note_pipeline/expanded.py
- 修改：video-to-note/tests/test_ai_expanded.py

- [ ] **步骤 1：编写失败的 Markdown 测试**

~~~python
def test_write_expanded_markdown_excludes_internal_details(self) -> None:
    payload = self._complete_payload_with_concept_and_operation()
    payload["audit"]["verification"] = [{
        "topic": "版本行为", "reason": "auto", "status": "verified",
        "reference_urls": ["https://example.com/docs"],
    }]
    output = self.temp_dir / "ai-expanded.md"

    write_expanded_markdown(payload, output, self.source)

    text = output.read_text(encoding="utf-8")
    self.assertIn("# 现代 R&B 和弦", text)
    self.assertIn("## 30 秒掌握", text)
    self.assertIn("## 和弦功能", text)
    self.assertIn("## 输入根音", text)
    self.assertNotIn("reference_urls", text)
    self.assertNotIn("source-faithful", text)
    self.assertNotIn("00:00", text)
~~~

- [ ] **步骤 2：运行测试确认失败**

运行任务 1 的测试命令。

预期：失败，因为 write_expanded_markdown 尚不存在。

- [ ] **步骤 3：实现最小 Markdown 写入器**

~~~python
def write_expanded_markdown(payload: dict[str, Any], output_path: Path, source_path: Path) -> None:
    validate_expanded_payload(payload, source_path)
    lines = [f"# {payload['title']}", "", "## 30 秒掌握", "", payload["thesis"], ""]
    for unit in payload["units"]:
        lines.extend(_render_unit(unit))
    if payload["application"]:
        lines.extend(["## 立即应用", ""])
        lines.extend(f"- {item}" for item in payload["application"])
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
~~~

_render_unit 只渲染当前单元实际存在的字段：概念写 core 与 plain，方法写判断与流程，操作写目标、步骤、检查点，事实写结论。禁止渲染 audit、source.path、sha256、URL、时间戳与 HTML。

- [ ] **步骤 4：补齐边界测试并验证**

新增断言：空 application 时没有“立即应用”；application 超过 3 项时失败；不存在的可选字段不会生成标题。运行 expanded 测试，预期全部通过。

### 任务 4：接入独立 CLI，保护 Source Faithful

**文件：**
- 修改：video-to-note/scripts/runtime/video_note_pipeline/cli.py:633-887
- 修改：video-to-note/tests/test_ai_expanded.py
- 修改：video-to-note/tests/test_source_import.py:22-45,131-140

- [ ] **步骤 1：编写失败的 CLI 集成测试**

~~~python
def test_cli_prepares_validates_and_writes_expanded_markdown(self) -> None:
    source = self._write_source("# 原视频笔记\n\n正文")
    draft = self.temp_dir / "expanded.json"
    output = self.temp_dir / "ai-expanded.md"

    self.assertEqual(main(["prepare-ai-expanded-note", str(source), str(draft), "--instruction", "讲得更通俗"]), 0)
    payload = json.loads(draft.read_text(encoding="utf-8"))
    payload.update(self._complete_payload_fields())
    draft.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    self.assertEqual(main(["validate-ai-expanded-note", str(draft), str(source)]), 0)
    self.assertEqual(main(["write-ai-expanded-markdown", str(draft), str(source), str(output)]), 0)
    self.assertTrue(output.exists())
~~~

在 test_source_import.py 增加断言：source-faithful 的 plan_commands 仍包含 --note-mode source-faithful，且不包含 prepare-ai-expanded-note。

将既有 test_skill_documents_source_faithful_boundary 的断言改为：source-faithful 仍是唯一主模式；SKILL.md 可以出现 ai-expanded 的独立阶段说明；source-faithful 的 rewrite-contract.md 仍不得出现 ai-expanded。

- [ ] **步骤 2：运行测试确认失败**

~~~powershell
. .\task-runtime.ps1
& $env:VIDEO_NOTE_PYTHON .\github-repo\video-to-note\video-to-note\tests\test_ai_expanded.py
& $env:VIDEO_NOTE_PYTHON .\github-repo\video-to-note\video-to-note\tests\test_source_import.py
~~~

预期：expanded 集成测试失败，提示命令不存在；source-faithful 回归通过。

- [ ] **步骤 3：实现三个 CLI 子命令**

~~~python
expanded_prepare_parser = subparsers.add_parser("prepare-ai-expanded-note")
expanded_prepare_parser.add_argument("source_markdown", type=Path)
expanded_prepare_parser.add_argument("output_json", type=Path)
expanded_prepare_parser.add_argument("--instruction", default="")

expanded_validate_parser = subparsers.add_parser("validate-ai-expanded-note")
expanded_validate_parser.add_argument("expanded_json", type=Path)
expanded_validate_parser.add_argument("source_markdown", type=Path)

expanded_write_parser = subparsers.add_parser("write-ai-expanded-markdown")
expanded_write_parser.add_argument("expanded_json", type=Path)
expanded_write_parser.add_argument("source_markdown", type=Path)
expanded_write_parser.add_argument("output_markdown", type=Path)
~~~

在 main 分发中调用 prepare_expanded_skeleton、load_expanded_payload、validate_expanded_payload、write_expanded_markdown，以 UTF-8 JSON 写入草稿。不要修改 VALID_NOTE_MODES，不要从 plan_commands 自动运行 expanded 命令，也不要调用 render-note。

- [ ] **步骤 4：运行两份测试确认通过**

运行步骤 2 的命令。

预期：expanded 和 source-faithful 全部通过。

- [ ] **步骤 5：手动命令行验收**

~~~powershell
. .\task-runtime.ps1
$runner = '.\github-repo\video-to-note\video-to-note\scripts\runtime\run_pipeline.ps1'
$source = '.\outputs\bilibili_BV17mKqzqEQC_retry\现代R&B和弦写作学习笔记.md'
$draft = '.\outputs\bilibili_BV17mKqzqEQC_retry\ai-expanded\draft.json'
& $runner prepare-ai-expanded-note $source $draft --instruction '我完全不会，带我学到能自己做出来；重点讲和弦选择；自动核查。'
~~~

预期：只生成 expanded 草稿；不修改原 Markdown，不下载媒体、不转写、不抽帧、不生成 HTML。最终写作仅在 AI 填充草稿后执行。

### 任务 5：编写契约并修正工作流文档

**文件：**
- 创建：video-to-note/references/ai-expanded-contract.md
- 修改：video-to-note/SKILL.md:14-68
- 修改：video-to-note/references/workflow.md:80-104
- 修改：video-to-note/tests/test_ai_expanded.py
- 修改：video-to-note/tests/test_source_import.py

- [ ] **步骤 1：编写失败的文档边界测试**

~~~python
def test_expanded_contract_preserves_two_artifact_boundary(self) -> None:
    root = Path(__file__).resolve().parents[1]
    contract = (root / "references" / "ai-expanded-contract.md").read_text(encoding="utf-8")
    workflow = (root / "references" / "workflow.md").read_text(encoding="utf-8")

    self.assertIn("source-faithful.md", contract)
    self.assertIn("ai-expanded.md", contract)
    self.assertIn("不显示时间戳", contract)
    self.assertIn("ai_advice_enabled 默认关闭", workflow)
~~~

在 test_source_import.py 中将原先 self.assertNotIn("ai-expanded", skill) 替换为下列边界断言：

~~~python
self.assertIn("source-faithful`（默认且唯一支持）", skill)
self.assertIn("ai-expanded", skill)
self.assertNotIn("ai-expanded", contract)
~~~

- [ ] **步骤 2：运行测试确认失败**

运行任务 1 的测试命令。

预期：失败，新契约不存在且 workflow 仍保留默认开启的旧表述。

- [ ] **步骤 3：编写 expanded 契约**

契约必须规定：

1. 读取冻结 source-faithful.md，不得修改它。
2. 原样保存用户自然语言要求；由 AI 判断“快速看懂 / 学到能用 / 深入掌握”。
3. auto 只核查高风险、明显矛盾、时效性或用户点名主题；联网失败不伪装为已验证。
4. 先生成动态单元规划，再生成最终 JSON；不输出时间戳、来源标记、核查报告、HTML 或空栏目。
5. 最终笔记是独立教材，不标记每段来自视频或 AI。

为 concept、method、operation、fact 各提供一份满足任务 2 schema 的最小 JSON 示例。

- [ ] **步骤 4：修订 Skill 与 workflow**

SKILL.md：只有用户明确请求“AI 重塑/扩展/典藏学习笔记”时，才在 source-faithful 验收后运行独立 expanded 阶段；最终交付 ai-expanded.md，不调用 HTML 渲染。

workflow.md：将“ai_advice_enabled 默认开启；用户关闭时省略 ai_advice。”替换为“source-faithful 中 ai_advice_enabled 默认关闭且必须为 false；AI 重塑仅在独立 ai-expanded 阶段执行。”

- [ ] **步骤 5：运行文档与回归验证**

~~~powershell
. .\task-runtime.ps1
& $env:VIDEO_NOTE_PYTHON .\github-repo\video-to-note\video-to-note\tests\test_ai_expanded.py
& $env:VIDEO_NOTE_PYTHON .\github-repo\video-to-note\video-to-note\tests\test_source_import.py
git -C .\github-repo\video-to-note diff --check
~~~

预期：全部通过；diff --check 无输出、退出码为 0。

### 任务 6：端到端验收与提交准备

**文件：**
- 修改：任务 1–5 的文件
- 不提交：docs/superpowers/plans/2026-08-02-note-modes.md、__pycache__/ 和临时 expanded 草稿

- [ ] **步骤 1：完成最小端到端演练**

用现有 R&B 的 source-faithful 笔记生成 expanded 草稿，填充至少一个 concept 和一个 method 或 operation，application 最多三项，然后运行：

~~~powershell
. .\task-runtime.ps1
$runner = '.\github-repo\video-to-note\video-to-note\scripts\runtime\run_pipeline.ps1'
& $runner validate-ai-expanded-note .\outputs\bilibili_BV17mKqzqEQC_retry\ai-expanded\draft.json .\outputs\bilibili_BV17mKqzqEQC_retry\现代R&B和弦写作学习笔记.md
& $runner write-ai-expanded-markdown .\outputs\bilibili_BV17mKqzqEQC_retry\ai-expanded\draft.json .\outputs\bilibili_BV17mKqzqEQC_retry\现代R&B和弦写作学习笔记.md .\outputs\bilibili_BV17mKqzqEQC_retry\ai-expanded\ai-expanded.md
~~~

预期：读者交付物只有 ai-expanded.md；其中没有 00:00、reference_urls、source-faithful、HTML 标签或核查报告字段。

- [ ] **步骤 2：验证 source-faithful 未变更**

~~~powershell
Get-FileHash .\outputs\bilibili_BV17mKqzqEQC_retry\现代R&B和弦写作学习笔记.md -Algorithm SHA256
~~~

预期：生成前后的哈希相同。

- [ ] **步骤 3：核对交付范围**

~~~powershell
git -C .\github-repo\video-to-note status --short
git -C .\github-repo\video-to-note diff --check
~~~

预期：只暂存任务 1–5 的源代码、测试和文档；缓存、旧计划和验证产物保持未暂存。

- [ ] **步骤 4：用户明确授权后再提交**

~~~powershell
git -C .\github-repo\video-to-note add -- video-to-note/scripts/runtime/video_note_pipeline/expanded.py video-to-note/scripts/runtime/video_note_pipeline/cli.py video-to-note/tests/test_ai_expanded.py video-to-note/tests/test_source_import.py video-to-note/references/ai-expanded-contract.md video-to-note/SKILL.md video-to-note/references/workflow.md
git -C .\github-repo\video-to-note commit -m "feat: add ai expanded study notes"
~~~

仅在用户明确要求提交时运行；不推送远程仓库。

## 计划自检

- 双产物边界：任务 1、3、4、5、6。
- 自然语言要求、按需核查和不暴露来源：任务 1、2、3、5。
- 动态知识结构、最少练习、无空栏目和无重复标题：任务 2、3。
- source-faithful 不变、无 HTML 和不重跑媒体处理：任务 4、6。
- 每项生产代码修改都有先失败、再实现、再通过的测试步骤；没有未定义类型、遗漏事项或无授权提交步骤。
