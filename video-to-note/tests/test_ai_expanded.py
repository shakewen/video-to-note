import json
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path


RUNTIME_ROOT = Path(__file__).resolve().parents[1] / "scripts" / "runtime"
sys.path.insert(0, str(RUNTIME_ROOT))


from video_note_pipeline.expanded import (
    ExpandedValidationError,
    prepare_expanded_skeleton,
    validate_expanded_payload,
    write_expanded_markdown,
)
from video_note_pipeline.cli import main


class AiExpandedTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self._temporary_directory.name)
        self.source = self._write_source("# 原视频笔记\n\n正文")

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def test_prepare_expanded_skeleton_keeps_instruction_and_source_digest(self) -> None:
        payload = prepare_expanded_skeleton(self.source, "重点讲实际用法；自动核查")

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["request"]["instruction"], "重点讲实际用法；自动核查")
        self.assertEqual(payload["source"]["sha256"], sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(payload["units"], [])
        self.assertEqual(payload["audit"]["verification"], [])

    def test_validate_expanded_payload_rejects_changed_source(self) -> None:
        payload = prepare_expanded_skeleton(self.source)
        self.source.write_text("# 被修改", encoding="utf-8")

        with self.assertRaisesRegex(ExpandedValidationError, "source-faithful 已变化"):
            validate_expanded_payload(payload, self.source)

    def test_validate_expanded_payload_accepts_dynamic_units(self) -> None:
        payload = self._complete_payload()
        payload["units"] = [
            {
                "type": "concept",
                "title": "和弦功能",
                "core": "它决定听感走向",
                "plain": "把它看成音乐里的角色分工。",
            },
            {
                "type": "operation",
                "title": "输入根音",
                "goal": "建立和弦骨架",
                "steps": ["新建轨道", "输入根音"],
                "checkpoints": ["根音与调性一致"],
            },
        ]

        result = validate_expanded_payload(payload, self.source)

        self.assertEqual(result["unit_count"], 2)

    def test_validate_expanded_payload_rejects_duplicate_unit_titles(self) -> None:
        payload = self._complete_payload()
        payload["units"] = [
            {"type": "concept", "title": "重复", "core": "a", "plain": "b"},
            {"type": "concept", "title": "重复", "core": "c", "plain": "d"},
        ]

        with self.assertRaisesRegex(ExpandedValidationError, "title 重复"):
            validate_expanded_payload(payload, self.source)

    def test_validate_expanded_payload_rejects_verified_audit_without_source(self) -> None:
        payload = self._complete_payload()
        payload["units"] = [
            {
                "type": "fact",
                "title": "核心结论",
                "conclusion": "先建立骨架，再修正细节。",
            }
        ]
        payload["audit"]["verification"] = [
            {
                "topic": "某软件版本行为",
                "reason": "auto",
                "status": "verified",
                "reference_urls": [],
            }
        ]

        with self.assertRaisesRegex(ExpandedValidationError, "必须保留来源"):
            validate_expanded_payload(payload, self.source)

    def test_validate_expanded_payload_keeps_verified_audit_internal(self) -> None:
        payload = self._complete_payload()
        payload["units"] = [
            {
                "type": "fact",
                "title": "核心结论",
                "conclusion": "先建立骨架，再修正细节。",
            }
        ]
        payload["audit"]["verification"] = [
            {
                "topic": "某软件版本行为",
                "reason": "targeted",
                "status": "verified",
                "reference_urls": ["https://example.com/docs"],
            }
        ]

        result = validate_expanded_payload(payload, self.source)

        self.assertEqual(result["unit_count"], 1)

    def test_validate_expanded_payload_rejects_source_reference_field(self) -> None:
        payload = self._complete_payload()
        payload["units"] = [
            {
                "type": "fact",
                "title": "核心结论",
                "conclusion": "先建立骨架，再修正细节。",
                "source_ref": "00:00-00:10",
            }
        ]

        with self.assertRaisesRegex(ExpandedValidationError, "不支持字段"):
            validate_expanded_payload(payload, self.source)

    def test_write_expanded_markdown_excludes_internal_details(self) -> None:
        payload = self._complete_payload_with_concept_and_operation()
        payload["audit"]["verification"] = [
            {
                "topic": "版本行为",
                "reason": "auto",
                "status": "verified",
                "reference_urls": ["https://example.com/docs"],
            }
        ]
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
        self.assertNotIn("## 立即应用", text)

    def test_write_expanded_markdown_only_adds_application_when_present(self) -> None:
        payload = self._complete_payload()
        payload["units"] = [
            {
                "type": "fact",
                "title": "核心结论",
                "conclusion": "先建立骨架，再修正细节。",
            }
        ]
        payload["application"] = ["用同一组和弦写一个四小节循环。"]
        output = self.temp_dir / "ai-expanded.md"

        write_expanded_markdown(payload, output, self.source)

        self.assertIn("## 立即应用", output.read_text(encoding="utf-8"))

    def test_cli_runs_the_separate_ai_expanded_flow(self) -> None:
        draft = self.temp_dir / "expanded.json"
        output = self.temp_dir / "ai-expanded.md"

        self.assertEqual(
            main(["prepare-ai-expanded-note", str(self.source), str(draft), "--instruction", "讲清实际用法"]),
            0,
        )
        payload = json.loads(draft.read_text(encoding="utf-8"))
        payload["title"] = "现代 R&B 和弦"
        payload["thesis"] = "先搭建骨架，再用听感修正细节。"
        payload["units"] = [
            {"type": "fact", "title": "核心结论", "conclusion": "先建立骨架，再修正细节。"}
        ]
        draft.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        self.assertEqual(main(["validate-ai-expanded-note", str(draft), str(self.source)]), 0)
        self.assertEqual(main(["write-ai-expanded-markdown", str(draft), str(self.source), str(output)]), 0)
        self.assertIn("# 现代 R&B 和弦", output.read_text(encoding="utf-8"))

    def _complete_payload_with_concept_and_operation(self) -> dict[str, object]:
        payload = self._complete_payload()
        payload["units"] = [
            {
                "type": "concept",
                "title": "和弦功能",
                "core": "它决定听感走向。",
                "plain": "把它看成音乐里的角色分工。",
            },
            {
                "type": "operation",
                "title": "输入根音",
                "goal": "建立和弦骨架。",
                "steps": ["新建轨道", "输入根音"],
                "checkpoints": ["根音与调性一致"],
            },
        ]
        return payload

    def _complete_payload(self) -> dict[str, object]:
        payload = prepare_expanded_skeleton(self.source)
        payload["title"] = "现代 R&B 和弦"
        payload["thesis"] = "先搭建和弦骨架，再用听感修正细节。"
        return payload

    def _write_source(self, content: str) -> Path:
        path = self.temp_dir / "source-faithful.md"
        path.write_text(content, encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
