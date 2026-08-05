# 完整转写 Markdown 设计

## 目标

每次转写在现有 JSON、SRT、TXT 之外，再生成 `full-transcript.md`。该文件是原始转写证据的可读交付物，不调用模型、不删减、不合并任何有效分段。

## 方案选择

1. 在现有 `transcribe.py` 内直接导出 Markdown（采用）：复用已规范化的分段，改动最小。
2. 引入 VideoCaptioner：会重复下载与 ASR 链路，且不能改善已存在的证据完整性。
3. 从 SRT 事后转换：丢失现有 JSON 的精确数据模型，并增加第二条转换链。

## 文件格式

`transcript/full-transcript.md` 使用 UTF-8：

```markdown
# 完整转写

> 原始转写记录：按时间顺序保留每个有效 Whisper 分段；未经 AI 改写。

## 00:00:01.200 → 00:00:03.400

原始分段文本
```

每个有效分段恰好对应一个二级标题和一个原文段落。时间戳精确到毫秒，使用 `HH:MM:SS.mmm`。

## 验证

单元测试以两个分段驱动 `write_transcript_outputs`，断言 Markdown 包含标题、免责声明、两段起止时间和两段原文，且原文顺序不变。交付验证器要求 `transcript/full-transcript.md` 存在。

## 范围外

- 不从 Markdown 推断软件操作或教学点。
- 不改变章节、HTML、抽帧、下载、ASR 模型或 AI 建议。
