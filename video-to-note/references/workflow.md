# 本地执行流程

将 Skill 根目录记为 `<skill_root>`，用户当前目录记为 `<workspace>`。运行器是 `<skill_root>/scripts/runtime/run_pipeline.ps1`。外部命令非零退出时立即停止。

## 0. 复用现有运行环境

如果 `<workspace>/task-runtime.ps1` 存在，先执行：

```powershell
. "<workspace>\task-runtime.ps1"
```

随后运行 `check_environment.ps1`。检查器按以下顺序自动匹配：

1. `VIDEO_NOTE_PYTHON`、`VIDEO_NOTE_YT_DLP`、`VIDEO_NOTE_FFMPEG`、`VIDEO_NOTE_FFPROBE`、`VIDEO_NOTE_BROWSER`。
2. `<workspace>/.video-note-runtime`。
3. 当前 `PATH`。
4. Windows 常见安装目录。

转写后端通过 `VIDEO_NOTE_TRANSCRIBE_BACKEND` 选择 `faster-whisper` 或 `openai-whisper`；未指定时自动检测。报告为 `ok` 时直接复用 `tools` 中的绝对路径继续，不安装或下载。只有四级匹配全部失败时，才判定依赖缺失。

报告为 `missing_tools` 时读取 `runtime-setup.md`，列出缺失项并先征得用户授权。依赖只写入 `<workspace>/.video-note-runtime`；不得全局安装或修改系统 `PATH`。安装超时后不得直接重试，先检查残留进程、虚拟环境模块和未完成压缩包。

## 1. 识别来源

```powershell
& "<skill_root>\scripts\init_request.ps1" `
  -Source "<视频链接或本地路径>" `
  -VideoType "<ui_demo|lecture|interview|mixed>" `
  -ContentDescription "<大致内容>"
```

读取返回的 `platform`、`video_id`、`config` 和 `output_root`。支持 B站、抖音、YouTube 和本地视频。只处理单个视频。

网络视频会选择：

```text
cookies/bilibili.txt
cookies/douyin.txt
cookies/youtube.txt
```

Cookie 不存在时不传给 yt-dlp。若平台提示登录、验证或访问受限，停止并提示用户补充对应文件。

## 2. 准备媒体

先运行：

```powershell
& "<skill_root>\scripts\runtime\run_pipeline.ps1" plan-commands <config>
```

### 网络视频

1. 执行 `download-source`。它调用全局 `video-downloader`，且固定传入 `--asr none`；下载器只负责视频、发布文案和元数据，不执行转写。
2. 命令将视频整理为 `media/source_video`，将规范化元数据写入 `metadata/metadata.full.json`，保留原始元数据为 `metadata/source_metadata.json`，并将发布文案写入 `metadata/post_caption.txt`。
3. 使用 `media/source_video` 通过 ffmpeg 提取 `media/audio.mp3`；转写统一由下一节的 Whisper 步骤执行一次。

### 本地视频

1. 执行 `write-local-metadata`，由 ffprobe 生成 `metadata.full.json`。
2. 用 ffmpeg 从原文件生成 `media/audio.mp3`。
3. 抽帧直接读取原视频，不复制大文件。
4. 作者、简介和标签未提供时保持为空，不得编造。

随后运行元数据审计。网络视频缺少关键字段时停止；本地视频缺少网络平台字段只记录说明。

## 3. 时长与转写

用 ffprobe 把 MP3 时长写入 `metadata/ffprobe_duration.txt`。中文使用 `turbo + zh`，英文使用 `small.en`。`faster-whisper` 通过 Skill 内置适配器写出兼容的 JSON、SRT 和 TXT；`openai-whisper` 保留原 CLI 路径。模型缓存统一使用：

```powershell
--model_dir "$env:VIDEO_NOTE_HOME\cache\whisper"
```

本地没有所需模型或缓存不完整时，直接下载或续传到 `<workspace>/.video-note-runtime/cache/whisper`，无需再次询问。默认 `turbo` 模型约 1.5 GB。网络超时后保留已有缓存并停止当前命令；下次运行继续使用同一缓存目录重试，不启动并行下载。

把 Whisper JSON 统一保存为 `transcript/transcript.json`，然后执行 `quality-gate`。元数据时长与音频差异超过 5%，或最后一个 segment 明显提前结束时，停止并报告。

## 4. 语义分章与一次 AI 重写

依次运行 `draft-chapters`、`prepare-cognitive-note`、`build-evidence-pack` 和 `prepare-actionable-note`。90 秒与 20 秒只用于候选边界，不能直接作为最终边界。

最终按话题、案例、操作目标和结论的语义完整性切章。同一案例的起因、过程和结果必须留在同一章。`adaptive-blocks-v1` 不设 12 章硬上限；超过 40 章时停止并检查是否把同一语义片段切得过碎。

只在此时读取 `learning-design.md` 与 `rewrite-contract.md`。一次读取证据包和骨架并写回 `chapters.actionable.json`，不要重复加载完整字幕。新任务必须提供一句 `author_statement`、`plain_rewrite` 和内部逐字 `source_quotes`。`ai_advice_enabled` 默认开启；用户关闭时省略 `ai_advice`。根据章节语义只选择需要的 `content_blocks`；没有明确迁移步骤时省略 `application`。写回前逐章检查标题、作者表达、内容块、截图和时间戳是否指向同一内容。

## 5. 截图、渲染与验收

操作演示章先运行 `plan-candidate-frames`，选择清晰时间点，再运行 `plan-frames`。本地视频把配置中的原文件路径作为抽帧输入。

依次运行：

```powershell
validate-actionable-note
render-note
plan-crop-commands
write-slice-manifest
verify-delivery
```

检查桌面和 390px 手机宽度：缺图为 0、横向溢出为 0、控制台错误为 0；远程样式、脚本和字体请求为 0；答题框、提交答案、评分和学习记录模块为 0。

长视频还要检查章节目录、当前章节提示、阅读进度和证据图延迟加载。最终向用户返回可整体搬运的离线目录，以及其中 `html/index.html`、`chapters.actionable.json` 和 `render-check` 的绝对路径。
