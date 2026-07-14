from pathlib import Path
from typing import Any

from .commands import format_command
from .config import validate_config
from .paths import build_output_paths


def render_manual_steps(config: dict[str, Any]) -> str:
    config = validate_config(config)
    video = config["video"]
    cookies = config["cookies"]
    language = config["language"]
    frames = config["frames"]
    output = config["output"]

    video_id = video["expected_id"]
    url = video["url"]
    platform = video.get("platform", "bilibili")
    source_kind = video.get("source_kind", "online_url")
    is_local = source_kind == "local_file" or platform == "local"
    cookies_mode = cookies.get("mode", "file")
    cookies_path = cookies.get("file_path", "./cookies.txt")
    primary_language = language.get("primary", "zh")
    video_type = frames.get("video_type", "mixed")
    frames_required = video_type in {"ui_demo", "mixed"}
    paths = build_output_paths(Path(output["root_dir"]), video_id)

    command_plan = [".\\pipeline\\run_pipeline.ps1", "plan-commands", "<your-config.yaml>"]
    metadata_audit = [
        ".\\pipeline\\run_pipeline.ps1",
        "audit-metadata",
        str(paths.metadata / "metadata.full.json"),
    ]
    quality_transcript = paths.transcript / ("transcript.zh.json" if primary_language == "en" else "<transcript>.json")
    quality_gate = [
        ".\\pipeline\\run_pipeline.ps1",
        "quality-gate",
        video_id,
        str(paths.metadata / "metadata.full.json"),
        str(paths.metadata / "ffprobe_duration.txt"),
        str(quality_transcript),
        str(paths.root / "quality_report.md"),
    ]
    draft_chapters = [
        ".\\pipeline\\run_pipeline.ps1",
        "draft-chapters",
        str(paths.transcript / ("transcript.zh.json" if primary_language == "en" else "<transcript>.json")),
        str(paths.root / "chapters.json"),
    ]
    if frames_required:
        draft_chapters.append("--include-frames")
    validate_chapters = [
        ".\\pipeline\\run_pipeline.ps1",
        "validate-chapters",
        str(paths.root / "chapters.json"),
    ]
    if frames_required:
        validate_chapters.append("--require-frames")
    render_note = [
        ".\\pipeline\\run_pipeline.ps1",
        "render-note",
        str(paths.metadata / "metadata.full.json"),
        str(paths.root / "chapters.json"),
        str(paths.html / "index.html"),
    ]
    if frames_required:
        render_note.append("--require-frames")
    verify_delivery = [".\\pipeline\\run_pipeline.ps1", "verify-delivery", str(paths.root)]
    if not frames_required:
        verify_delivery.append("--no-require-frames")
    write_slice_manifest = [
        ".\\pipeline\\run_pipeline.ps1",
        "write-slice-manifest",
        str(paths.render_check / "fullpage.png"),
        str(paths.render_check / "slice_manifest.json"),
        "--slice-height",
        "1800",
        "--overlap",
        "100",
    ]

    whisper_note = "turbo + zh"
    if primary_language == "en":
        whisper_note = "small.en"

    lines = [
        f"# Manual Steps: {video_id}",
        "",
        "## 0. 准备输入",
        f"- 视频 URL: {url}",
        f"- 输出目录: `{paths.root}`",
        f"- 视频类型: `{video_type}`",
        f"- 先运行 `{format_command(command_plan)}` 生成完整机器命令清单。",
        "",
    ]
    if is_local:
        lines.extend(
            [
                "## 1. 准备本地视频",
                "- 本地视频无需 Cookie，流水线直接读取原文件，不重复复制源视频。",
                f"- 确认文件仍然存在：`{url}`。",
            ]
        )
    elif cookies_mode == "browser":
        lines.append(f"## 1. 准备 {platform} Cookie")
        browser = cookies.get("browser", "<browser>")
        lines.append(f"- 使用浏览器 Cookie 模式，确认 `{browser}` 已登录 {platform}。")
    elif cookies_mode == "optional_file":
        lines.extend(
            [
                f"## 1. 准备 {platform} Cookie",
                f"- Cookie 文件放在 `{cookies_path}`；公开内容可不提供。",
                "- 如果平台提示登录、验证或访问受限，停止并补充对应 Cookie，不自动反复重试。",
            ]
        )
    else:
        lines.extend(
            [
                f"## 1. 准备 {platform} Cookie",
                f"- 从已登录 {platform} 的浏览器导出 Cookie，保存为 `{cookies_path}`。",
            ]
        )
    lines.extend(
        [
            "- Cookie 只放本机，不要公开提交或发给别人。" if not is_local else "- 原视频路径只用于本机处理，不会写进 Skill 安装包。",
            "",
            "## 2. 获取完整元数据",
            "- 执行 `plan-commands` 里的 Metadata 命令。网络视频由 yt-dlp 抓取；本地视频由 ffprobe 读取。",
            f"- 随后运行 `{format_command(metadata_audit)}`。",
            "- 网络视频检查标题、作者、简介、标签、封面和时长；本地视频没有作者、简介或标签时保持为空，不得编造。",
            "",
            "## 3. 下载音频并校验时长",
            "- 执行 Best Audio to MP3 命令，下载最佳音频并转成 mp3。",
            "- 执行 ffprobe Duration Check 命令，把输出保存到 `metadata/ffprobe_duration.txt`。",
            f"- 转写完成后运行 `{format_command(quality_gate)}`，生成 `quality_report.md`。",
            "- 这个 gate 会检查音频时长和元数据时长差异超过 5% 的情况，也会检查最后一个 Whisper segment 是否接近音频结尾。",
            "- 如果 action 是 `redownload_or_mark_abnormal`，先重下音频；仍然不一致就把本视频标记为异常，不要悄悄忽略。",
            "",
            "## 4. Whisper 转写",
            f"- 当前语言配置使用 `{whisper_note}`。",
            "- 中文视频使用 turbo + zh；英文视频使用 small.en 先转写英文。",
        ]
    )
    if primary_language == "en":
        lines.extend(
            [
                "- 英文视频还要运行 `draft-translation`，逐段人工翻成中文。",
                "- 填好 `zh_text` 后运行 `finalize-translation`，再用中文 transcript 进入章节草稿。",
            ]
        )
    lines.extend(
        [
            "- 再运行 `quality-gate`，确认最后一个 Whisper segment 的结束时间接近音频总时长。",
            "",
            "## 5. 拆章和写正文",
            f"- 先运行 `{format_command(draft_chapters)}` 生成 `chapters.json` 草稿。",
            "- 人工按视频自然结构改章节，不要机械套模板。",
            "- 每章写白话短句：问题、陷阱、步骤、结论按内容需要出现；保留可回跳时间戳、要点、关键引用、视觉锚点。",
            "",
            "## 6. 为每章生成真实 SVG 图解",
            "- SVG 必须来自本章真实内容：流程画路径，概念画关系/分层，时间变化画时间线，对比画矩阵，风险误区画检查表或决策树，数据画简图，因果画链路。",
            "- 每张图都要有关键词、关系、箭头或标签；不要做装饰图，也不要复制同一个壳。",
            "",
            "## 7. 抽取真实视频帧",
        ]
    )
    if frames_required:
        lines.extend(
            [
                "- 这是界面/操作演示类视频，每章除了 SVG 之外还必须有真实截图。",
                "- 先运行 `plan-candidate-frames`，长视频按章节时间段抽候选帧。",
                "- 从候选里挑信息量最大、界面最清晰的一帧，再运行 `plan-frames` 里的 ffmpeg 命令。",
                "- 最终帧命名要带阶段名和秒数，使用 `-ss` 精确定位、`-q:v 1` 最高质量。",
            ]
        )
    else:
        lines.extend(
            [
                "- 非界面演示视频可按需要配截图；如果章节依赖画面证据，仍然用 `plan-candidate-frames` 选帧。",
                "- 如果启用 `--require-frames`，每章都必须提供相对路径截图。",
            ]
        )
    lines.extend(
        [
            "",
            "## 8. 渲染离线 HTML",
            f"- 先运行 `{format_command(validate_chapters)}`。",
            f"- 再运行 `{format_command(render_note)}`。",
            "- 页面结构保持：正文 -> SVG 图解 -> 视频时间戳截图。"
            if frames_required
            else "- 页面结构保持：正文 -> SVG 图解；需要画面证据的章节再追加视频时间戳截图。",
            "- CSS 和 SVG 内联；真实截图使用相对路径，并和 HTML 放在同一输出目录树里，保证离线可看。",
            "",
            "## 9. 截整页、查空白、切片",
            "- 执行 Chrome Headless Render Check 命令生成整页 PNG。",
            "- 运行 `inspect-png` 检查截图尺寸、空白和渲染结果；人工再看一遍有没有重叠、图片缺失或标题被遮挡。",
            "- 运行 `plan-crop-commands`，再执行生成的 ffmpeg crop 命令；切片保留约 100px 重叠，必要时调整 y 偏移避免切断标题。",
            f"- 执行切片后运行 `{format_command(write_slice_manifest)}`，写出 `render-check/slice_manifest.json` 供最终验收检查覆盖范围和重叠。",
            "",
            "## 10. 最终验收",
            f"- 运行 `{format_command(verify_delivery)}`。",
            "- 确认 HTML、元数据、mp3、转写、章节 JSON、真实截图、整页 PNG 和切片都在输出目录中。",
            "- 任一检查失败时，回到对应步骤修复；不要把异常当作成品交付。",
        ]
    )
    return "\n".join(lines) + "\n"
