# 完整转写 Markdown 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 从现有 Whisper 分段生成完整、带起止时间戳的 Markdown 转写文件。

**架构：** 复用 `transcribe.py` 的 `_normalize_segments` 结果，在同一写入函数中额外生成 Markdown。交付检查只验证文件存在，不改变章节笔记和渲染流程。

**技术栈：** Python 标准库、unittest。

---

### 任务 1：导出完整转写 Markdown

**文件：**
- 修改：`video-to-note/tests/test_source_import.py`
- 修改：`video-to-note/scripts/runtime/video_note_pipeline/transcribe.py`
- 修改：`video-to-note/scripts/runtime/video_note_pipeline/delivery.py`

- [ ] **步骤 1：编写失败的测试**

```python
def test_transcript_outputs_include_complete_markdown(self) -> None:
    outputs = write_transcript_outputs(...)
    markdown = outputs["markdown"].read_text(encoding="utf-8")
    self.assertIn("## 00:00:01.200 → 00:00:03.400", markdown)
    self.assertLess(markdown.index("第一段"), markdown.index("第二段"))
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest video-to-note/tests/test_source_import.py -v`

预期：FAIL，`KeyError: 'markdown'`。

- [ ] **步骤 3：编写最少实现代码**

```python
markdown_path = output_dir / "full-transcript.md"
markdown_path.write_text(markdown_text, encoding="utf-8")
return {"json": json_path, "srt": srt_path, "txt": txt_path, "markdown": markdown_path}
```

并在 `verify_delivery` 中调用 `_check_file(checks, root, "transcript/full-transcript.md")`。

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest video-to-note/tests/test_source_import.py -v`

预期：PASS。

- [ ] **步骤 5：运行完整相关测试**

运行：`python -m unittest discover -s video-to-note/tests -v`

预期：PASS。
