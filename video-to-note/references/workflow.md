# 本地执行流程

将 Skill 根目录记为 `<skill_root>`，用户当前目录记为 `<workspace>`。运行器是 `<skill_root>/scripts/runtime/run_pipeline.ps1`。外部命令非零退出时立即停止。

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

1. 执行 Metadata 命令，把 stdout 用 UTF-8 无 BOM 写入 `metadata/metadata.full.json`，禁止用 Windows PowerShell 的 `>`。
2. 下载结果固定为 `media/audio.mp3` 和 `media/video.mp4`。
3. 强制使用 `--no-playlist`，防止误下载合集。

### 本地视频

1. 执行 `write-local-metadata`，由 ffprobe 生成 `metadata.full.json`。
2. 用 ffmpeg 从原文件生成 `media/audio.mp3`。
3. 抽帧直接读取原视频，不复制大文件。
4. 作者、简介和标签未提供时保持为空，不得编造。

随后运行元数据审计。网络视频缺少关键字段时停止；本地视频缺少网络平台字段只记录说明。

## 3. 时长与转写

用 ffprobe 把 MP3 时长写入 `metadata/ffprobe_duration.txt`。中文使用 `turbo + zh`，英文使用 `small.en`，并强制设置：

```powershell
--model_dir "$env:VIDEO_NOTE_HOME\cache\whisper"
```

把 Whisper JSON 统一保存为 `transcript/transcript.json`，然后执行 `quality-gate`。元数据时长与音频差异超过 5%，或最后一个 segment 明显提前结束时，停止并报告。

## 4. 自然分章与一次 AI 重写

依次运行 `draft-chapters`、`prepare-cognitive-note`、`build-evidence-pack` 和 `prepare-actionable-note`。90 秒与 20 秒只用于候选边界，最终按主题完整性合并，通常不超过 12 章。

只在此时读取 `rewrite-contract.md`。一次读取证据包和骨架并写回 `chapters.actionable.json`，不要重复加载完整字幕。

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

检查桌面和 390px 手机宽度：缺图为 0、横向溢出为 0、控制台错误为 0。最终向用户返回 `html/index.html`、`chapters.actionable.json` 和 `render-check` 的绝对路径。
