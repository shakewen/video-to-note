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

默认语言为中文。网络视频按平台读取当前工作目录下的 `cookies/<平台>.txt`；文件不存在时先按公开内容处理，平台要求登录时再提示用户补充。

先定位本文件所在目录为 `<skill_root>`。自带脚本从 `<skill_root>` 调用，用户输出写入当前工作目录。

## 执行

1. 运行 `<skill_root>/scripts/check_environment.ps1`。
2. 运行 `<skill_root>/scripts/init_request.ps1 -Source <输入>`，自动识别来源并生成配置。
3. 读取 `references/workflow.md`，完成采集或本地读取、时长校验、Whisper、质量门禁和证据包。
4. 仅在重写 `chapters.actionable.json` 时读取 `references/rewrite-contract.md`。
5. 按内容自然切分，通常 5 至 12 章；动态选择 `sop`、`concept`、`matrix` 或 `brief`，不得凑数。
6. 执行正式抽帧、HTML 渲染和交付验证；返回绝对路径。

## Token 限制

- 下载、转写、候选切章、SVG、HTML、截图和校验全部交给本地脚本。
- 原始字幕只进入一次结构化重写。
- 不生成举一反三案例，只保留作者真实案例。
- 模型只输出 `diagram_spec`，SVG 由本地脚本绘制。
- 相同工具、背景和结论只写一次。

## 边界

- 首版只处理单个视频或指定分 P，不处理播放列表、合集或账号主页。
- 作者未演示的按钮、参数和步骤不得写成视频事实。
- AI 通俗解释必须明确标注。
- 不输出 Cookie、密码、破解步骤或未公开敏感信息。
