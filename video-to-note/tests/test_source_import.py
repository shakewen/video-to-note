import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


RUNTIME_ROOT = Path(__file__).resolve().parents[1] / "scripts" / "runtime"
sys.path.insert(0, str(RUNTIME_ROOT))

from video_note_pipeline.source_import import import_downloader_result
from video_note_pipeline.commands import build_video_downloader_command, build_whisper_command
from video_note_pipeline.cli import plan_commands
from video_note_pipeline.transcribe import write_transcript_outputs


class SourceImportTests(unittest.TestCase):
    def test_transcript_outputs_include_complete_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            outputs = write_transcript_outputs(
                root / "audio.mp3",
                root / "transcript",
                "zh",
                [
                    {"start": 1.2, "end": 3.4, "text": "第一段操作说明"},
                    {"start": 5.0, "end": 6.0, "text": "第二段教学说明"},
                ],
            )

            markdown = outputs["markdown"].read_text(encoding="utf-8")

            self.assertIn("# 完整转写", markdown)
            self.assertIn("未经 AI 改写", markdown)
            self.assertIn("## 00:00:01.200 → 00:00:03.400", markdown)
            self.assertIn("## 00:00:05.000 → 00:00:06.000", markdown)
            self.assertLess(markdown.index("第一段操作说明"), markdown.index("第二段教学说明"))

    def test_whisper_defaults_to_faster_whisper_adapter(self) -> None:
        with patch.dict("os.environ", {"VIDEO_NOTE_TRANSCRIBE_BACKEND": ""}):
            command = build_whisper_command("C:/output/audio.mp3", "zh", "C:/output/transcript")

        self.assertIn("transcribe.py", command[1])
        backend_index = command.index("--backend")
        self.assertEqual(command[backend_index + 1], "faster-whisper")

    def test_skill_documents_single_asr_pipeline_without_platform_subtitles(self) -> None:
        skill_path = Path(__file__).resolve().parents[1] / "SKILL.md"
        skill = skill_path.read_text(encoding="utf-8")

        self.assertIn("video-downloader", skill)
        self.assertIn("--asr none", skill)
        self.assertNotIn("平台字幕", skill)

    def test_plan_uses_downloader_then_single_whisper_transcript(self) -> None:
        plan = plan_commands(
            {
                "video": {"url": "https://example.invalid/video", "expected_id": "demo"},
                "cookies": {"mode": "none"},
                "language": {"primary": "zh"},
                "frames": {"video_type": "lecture"},
                "output": {"root_dir": "C:/output"},
            }
        )

        self.assertIn("download-source", plan)
        self.assertIn("Whisper Transcript", plan)
        self.assertNotIn("Platform Subtitle", plan)

    def test_build_video_downloader_command_disables_its_asr(self) -> None:
        command = build_video_downloader_command(
            "https://example.invalid/video",
            "C:/output/source",
            "C:/tools/download_video.py",
        )

        self.assertEqual(command[-2:], ["--asr", "none"])
        self.assertIn("C:/tools/download_video.py", command)

    def test_build_video_downloader_command_accepts_current_python(self) -> None:
        command = build_video_downloader_command(
            "https://example.invalid/video",
            "C:/output/source",
            "C:/tools/download_video.py",
            python_executable="C:/runtime/python.exe",
        )

        self.assertEqual(command[0], "C:/runtime/python.exe")

    def test_import_downloader_result_preserves_metadata_and_moves_video(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "downloader"
            source_dir.mkdir()
            video_path = source_dir / "original.mp4"
            video_path.write_bytes(b"video")
            caption_path = source_dir / "post_caption.txt"
            caption_path.write_text("发布文案", encoding="utf-8")
            metadata_path = source_dir / "metadata.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "title": "测试视频",
                        "description": "说明",
                        "tags": ["测试"],
                        "source_url": "https://example.invalid/video",
                        "author": {"nickname": "作者"},
                        "video": {"duration_seconds": 12.5},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            manifest = import_downloader_result(
                {
                    "platform": "bilibili",
                    "id": "BV-test",
                    "video_path": str(video_path),
                    "metadata_path": str(metadata_path),
                    "post_caption_path": str(caption_path),
                },
                root / "output",
            )

            self.assertEqual(manifest["video_path"], str(root / "output" / "media" / "source_video"))
            self.assertTrue((root / "output" / "media" / "source_video").is_file())
            self.assertFalse(video_path.exists())
            metadata = json.loads((root / "output" / "metadata" / "metadata.full.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["duration"], 12.5)
            self.assertEqual(metadata["uploader"], "作者")
            self.assertTrue((root / "output" / "metadata" / "post_caption.txt").is_file())


if __name__ == "__main__":
    unittest.main()
