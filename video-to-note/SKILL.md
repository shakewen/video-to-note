---
name: video-to-note
description: 用于用户提供 B站、抖音、YouTube 链接或本地视频路径，并要求制作、继续或检查可操作视频笔记时。
---

# 视频转可操作笔记

使用 Windows PowerShell 和本 Skill 自带的本地流水线。每条外部命令后检查退出码；失败时停止并说明原因，不盲目重试。

## 收集输入

只询问并确认一次：

1. 单个视频链接或本地视频文件路径。
2. 视频类型和大致内容。
3. 颜色与排版；未填写时使用 `reference-warm`。
4. 笔记模式：`source-faithful`（默认且主流程唯一支持）。

默认语言为中文。网络视频按平台读取当前工作目录下的 `cookies/<平台>.txt`；文件不存在时先按公开内容处理，平台要求登录时再提示用户补充。

先定位本文件所在目录为 `<skill_root>`。自带脚本从 `<skill_root>` 调用，用户输出写入当前工作目录。

## 执行

1. 当前目录存在 `task-runtime.ps1` 时，必须点源而不是作为子进程执行：
   ```powershell
   . ".\task-runtime.ps1"
   & "<skill_root>\scripts\check_environment.ps1" -RuntimeRoot $env:VIDEO_NOTE_HOME
   ```
   未点源任务配置时，`<skill_root>/scripts/check_environment.ps1` 的缺失检查结果无效，禁止据此报告缺失或启动安装。没有任务配置或正确加载后仍返回 `missing_tools` 时，读取 `references/runtime-setup.md`。
2. 运行 `<skill_root>/scripts/init_request.ps1 -Source <输入> -NoteMode <模式>`，自动识别来源并生成配置。
3. 网络视频通过内置 `download-source` 命令调用全局 `video-downloader`；该调用必须传入 `--asr none`，只下载视频、发布文案和元数据。随后由本 Skill 的 `faster-whisper` 完成唯一一次带时间戳的转写。读取 `references/workflow.md`，完成采集或本地读取、时长校验、Whisper、质量门禁和证据包。
4. 在重写 `chapters.actionable.json` 前完整读取 `references/learning-design.md` 和 `references/rewrite-contract.md`，并严格按 `note.mode` 选择内容边界。
5. 按话题、案例、操作目标和结论的语义边界切章，不按固定时长或固定章数机械切割。
6. 新任务使用 `learning_design_version: "adaptive-blocks-v1"`：逐字 `source_quotes` 只用于证据回溯。`source-faithful` 关闭 AI 建议，只保留作者实际讲解或演示的内容。
7. 执行正式抽帧、离线 HTML 渲染和交付验证；返回整个离线目录的绝对路径。

## AI 重塑（仅用户明确要求的独立阶段）

`ai-expanded` 不属于 `note.mode`，不会重跑下载、转写、抽帧或改写 source-faithful。只有用户确认 source-faithful 后，才读取 `references/ai-expanded-contract.md`，基于冻结的 Markdown 创建全新的可收藏学习笔记。

用户只需用自然语言说明目标，例如“让我快速看懂并能马上用”“我有基础，重点纠正和扩展实际用法”“重点讲和弦选择；自动核查；不要讲混音”。没有说明时，默认“讲明白，并让我能马上使用，不啰嗦”。

先用一次完整的 source-faithful 输入提取精简的待核查主张和学习结构；随后只将这些主张交给 `Agent Reach` 搜索，最后用“学习结构 + 核查结论”写 Markdown，不再次读取完整 source-faithful。不得逐句搜索、不得把字幕、截图或整篇笔记交给联网检索。

依次执行：

```powershell
& "<skill_root>\scripts\runtime\run_pipeline.ps1" prepare-ai-expanded-note <source-faithful.md> <expanded.json> --instruction "<用户说明>"
# 由 AI 依照 ai-expanded-contract.md 填充 expanded.json
& "<skill_root>\scripts\runtime\run_pipeline.ps1" validate-ai-expanded-note <expanded.json> <source-faithful.md>
& "<skill_root>\scripts\runtime\run_pipeline.ps1" write-ai-expanded-markdown <expanded.json> <source-faithful.md> <ai-expanded.md>
```

最终只交付 `ai-expanded.md`。不生成 HTML，不向读者输出时间戳、原视频与 AI 的对照、核查链接或内部审计信息。

## Token 限制

- `source-faithful` 只进行一次忠实整理：完整转写、截图与覆盖表由本地流水线处理；只在“画面做了但没有说出”的操作处审看截图，不逐帧交给模型。
- `source-faithful` 最终只输出 Markdown 与离线 HTML；内部覆盖表不进入读者页面。仅被顺带提及、或作者明确说本课不展开的内容不必收录。
- 下载、转写、候选切章、SVG、HTML、截图和校验全部交给本地脚本。
- 带时间戳的转写文本只进入一次结构化重写。
- 不生成举一反三案例，只保留作者真实案例。
- 模型只输出 `diagram_spec`，SVG 由本地脚本绘制。
- 相同工具、背景和结论只写一次。
- 不要求读者答题、输入命令、提交答案或等待 GPT 评价。

## 环境与安装规则

- 本机环境自动匹配顺序：`VIDEO_NOTE_*` 显式路径 → 当前项目 `.video-note-runtime` → 当前 `PATH` → Windows 常见安装目录。
- 显式路径优先：若显式路径无效，报告配置错误，不静默回退到其他版本。
- 转写优先复用当前 Python 中的 `faster-whisper`；需要兼容旧环境时才使用 `openai-whisper` CLI。
- 转写模型下载例外：用户启动视频笔记任务即视为持续授权。所需模型不存在或下载不完整时，无需再次询问，直接下载或续传到当前项目 `.video-note-runtime/cache/whisper`；默认 `turbo` 模型约 1.5 GB。
- 该模型下载例外不得扩展到 Python、FFmpeg、ffprobe、yt-dlp、浏览器或其他依赖。
- 工具不在当前 `PATH` 不等于未安装。只有四级匹配全部失败后，才报告缺失。
- `task-runtime.ps1` 中已有显式路径时先验证并复用，不得被临时设置的环境变量覆盖；环境检查前必须确认配置已经点源到当前 PowerShell 进程。
- 缺失时先读取 `references/runtime-setup.md`、列出 `missing_tools` 并先征得用户授权；依赖只允许写入当前项目的 `.video-note-runtime`。
- 不得全局安装、修改系统 `PATH` 或默认调用 `winget install`。除上述转写模型外，未经用户明确授权，不执行 `pip install`、下载安装器或便携依赖下载。
- 任何安装前必须完成 `references/runtime-setup.md` 的安装前去重门禁；安装或下载超时后先检查残留进程、已有文件和损坏下载包，不得启动第二个安装进程。

## 边界

- `source-faithful` 不扩展、不纠错、不补充；只记录视频中实际解释、推导、演示或操作过的内容。
- 首版只处理单个视频或指定分 P，不处理播放列表、合集或账号主页。
- 作者未演示的按钮、参数和步骤不得写成视频事实。
- 章节标题、作者原例、正文、截图和时间戳必须属于同一语义片段。
- `ai-expanded` 只能在独立阶段读取已验收的 source-faithful Markdown；不得覆盖它或接入主流程 `note.mode`。
- 网页的核心学习路径必须完全离线可用；不得依赖 CDN、在线字体或远程脚本。
- 不输出 Cookie、密码、破解步骤或未公开敏感信息。
