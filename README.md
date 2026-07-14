# Skill介绍：

## 安装方法 一：让 Agent 自动安装

适用于 Codex、Claude Code、Gemini CLI 等能够读写本地文件并执行终端命令的 Agent。普通网页聊天机器人没有本地权限，不能代装。

打开 GitHub 项目页面，点击绿色的 **Code**，再点击 **Download ZIP**。

1. 下载好的ZIP文件，解压到任意盘。
2. 在 Agent 中打开解压后的文件夹。
3. 把下面这段话发给 Agent，把路径换成你自己的：

```text
请安装 D:\下载目录\video-to-note 里的视频笔记 Skill。
安装目标：Codex、Claude Code、GitHub Copilot、Gemini CLI。
模型和运行缓存必须放在 D:\VideoNoteRuntime。（指定任意位置）
请先设置 VIDEO_NOTE_HOME，再检查并安装缺少的环境。
每一步检查执行结果，出错立即停止并用大白话告诉我原因。
```

Agent 执行完后，重新打开你要使用的 Agent。Skill就安装完毕了。

下面的 **PowerShell** 步骤是给希望自己操作的人准备的。

## 二、如何从 GitHub 下载并使用

### 1. 下载文件

打开 GitHub 项目页面，点击绿色的 **Code**，再点击 **Download ZIP**。

下载完成后：

1. 找到 ZIP 文件。
2. 右键选择“全部解压缩”。
3. 打开解压后的文件夹。

如果不会用 Git，请直接使用上面的 **Download ZIP**，不用输入命令。

如果已经装了 Git，手动操作：按键盘 `Win` 键，搜索并打开“PowerShell”，复制下面的命令，把仓库地址换成真实地址，再按回车：

```powershell
git clone https://github.com/shakewen/video-to-note.git
```



### 2. 手动安装 Skill

手动操作：打开解压后的文件夹，点击文件管理器顶部的地址栏，输入 `powershell`，然后按回车。终端会自动在当前文件夹打开。

手动操作：在刚打开的终端中复制下面这行，按回车。它只允许当前窗口运行安装脚本，关闭窗口后自动失效：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

手动操作：继续在同一个终端中复制下面这行，按回车。它会把 Skill 安装给四个平台，但不会重复安装 ffmpeg 或 Whisper：

```powershell
& ".\video-to-note\scripts\install_skill.ps1" -Agent All
```

如果只使用一个平台，请只执行下面对应的那一条，不要四条全部执行。

手动操作：只使用 Codex 时，复制下面这行并按回车：

```powershell
& ".\video-to-note\scripts\install_skill.ps1" -Agent Codex
```

手动操作：只使用 Claude Code 时，复制下面这行并按回车：

```powershell
& ".\video-to-note\scripts\install_skill.ps1" -Agent Claude
```

手动操作：只使用 GitHub Copilot 时，复制下面这行并按回车：

```powershell
& ".\video-to-note\scripts\install_skill.ps1" -Agent Copilot
```

手动操作：只使用 Gemini CLI 时，复制下面这行并按回车：

```powershell
& ".\video-to-note\scripts\install_skill.ps1" -Agent Gemini
```

`Both` 是旧的快捷选项，只安装到 Codex 和 Claude Code。

默认安装位置：

```text
Codex          C:\Users\你的用户名\.codex\skills\video-to-note
Claude Code    C:\Users\你的用户名\.claude\skills\video-to-note
GitHub Copilot C:\Users\你的用户名\.copilot\skills\video-to-note
Gemini CLI     C:\Users\你的用户名\.gemini\skills\video-to-note
```

安装完成后，重新打开对应 Agent。Gemini CLI 也可以输入 `/skills reload` 立即重新扫描。

#### 问题回答：直接复制到 Codex 的 Skills 目录可以吗？

可以，但必须同时满足三点：

1. 复制整个 `video-to-note` 文件夹，不能只复制 `SKILL.md`。
2. 最终必须是 `...\.codex\skills\video-to-note\SKILL.md`，不能多套一层同名文件夹。
3. 复制后重新打开 Codex 或新建一个任务，让它重新扫描 Skills。

只要 `SKILL.md`、`scripts`、`references` 和 `assets` 都在，Codex 就能识别规则并调用配套脚本。电脑上的 ffmpeg、Whisper、yt-dlp 和 Edge 仍要单独准备。

#### 其他 Agent 怎么安装？

先查清它的个人 Skills 根目录。手动操作：在解压目录的 PowerShell 中复制下面三行，把示例目录换成真实目录，然后按回车：

```powershell
& ".\video-to-note\scripts\install_skill.ps1" `
  -Agent Custom `
  -TargetSkillsRoot "D:\某个Agent\skills"
```

脚本会自动生成 `D:\某个Agent\skills\video-to-note`。前提是该 Agent 支持 `SKILL.md` 形式的 Agent Skills；如果它只支持插件、扩展或自定义提示词，单纯复制文件夹不会生效。

### 3. 先把模型缓存固定到 D 盘

这一步不是 Whisper 的硬性要求，但想保护 C 盘就应该在第一次转写前执行。

手动操作：在 PowerShell 中完整复制下面五行，按回车。执行成功时通常不会显示文字：

```powershell
[Environment]::SetEnvironmentVariable(
  "VIDEO_NOTE_HOME",
  "D:\VideoNoteRuntime",
  "User"
)
```

关闭当前 PowerShell，再按照前面的方法重新打开。Whisper 模型第一次下载时会直接放在：

```text
D:\VideoNoteRuntime\cache\whisper
```

### 4. 检查电脑还缺什么

手动操作：回到解压后的文件夹，点击地址栏，输入 `powershell` 并按回车；然后复制下面三行，再按回车：

```powershell
& ".\video-to-note\scripts\check_environment.ps1" `
  -RuntimeRoot "D:\VideoNoteRuntime"
```

看到 `"status": "ok"`，说明工具已经齐全。

如果结果提示缺少 Python 包，手动操作：在同一个终端中复制下面四行并按回车：

```powershell
& ".\video-to-note\scripts\check_environment.ps1" `
  -RuntimeRoot "D:\VideoNoteRuntime" `
  -InstallPythonPackages
```

这会安装 yt-dlp、Whisper 和 Pillow。**ffmpeg** 与 **Edge** 仍需单独安装。

### 5. 准备各平台 Cookie

Cookie是非常重要的用户数据，要自己保存好不要泄露！

#### 5.1 获取Cookie（简单方式）

```text
去Edge浏览器中下载一个名字叫Cookie-Editor的插件
下载完成后打开你想要转化为笔记的视频，停留在当前页面即可
单击插件点击右下角的Export选择NetScape即可导出当前视频播放页面的Cookie文件
```

在以后存放笔记的工作文件夹里，新建 `cookies` 文件夹：

```text
cookies/
├─ bilibili.txt    B站
├─ douyin.txt      抖音
├─ youtube.txt     YouTube
```

不需要一次准备三个。使用哪个平台，就放哪个文件。

- YouTube视频可能不需要 Cookie。
- 平台提示登录或验证时，再补对应 Cookie。
- 本地视频不需要 Cookie。
- Cookie 不要上传 GitHub，也不要发给别人。

### 6. 开始生成笔记

在 Codex 中输入：

```text
使用 $video-to-note
视频链接或本地路径：https://……
视频类型和大致内容：完整软件教程，主要讲……
颜色与排版：暖白简洁，重点突出步骤
```

本地视频这样写：

```text
使用 $video-to-note
视频链接或本地路径：D:\Videos\我的教程.mp4
视频类型和大致内容：完整操作教程
颜色与排版：暖白简洁
```

Claude Code 把第一行改成：

```text
/video-to-note
```

GitHub Copilot 和 Gemini CLI 直接写“使用 video-to-note”，再附上视频链接、视频类型和配色要求即可。

Skill 会自动判断是 B站、抖音、YouTube 还是本地文件。

### 7. 查看结果

最终网页在：

```text
outputs\<平台_视频ID>\html\index.html
```

双击 `index.html` 即可离线查看。

其他常用文件：

```text
chapters.actionable.json   笔记正文
media\audio.mp3            转写音频
transcript\                Whisper 字幕
html\frames\              正式截图
render-check\              页面长图和切片
```

## 二、支持哪些输入

支持：

- B站单视频或指定分 P。
- 抖音单条作品。
- YouTube 单视频。
- 本地 MP4、MKV、MOV、AVI、WebM、M4V、FLV、TS 等视频文件。

暂时不支持一次下载整个播放列表、合集或账号主页，防止误下载几十个视频。

## 三、常见问题

### 提示需要登录或验证

停止当前任务，把对应平台 Cookie 放进 `cookies` 文件夹，再重新开始。不要连续盲目重试。

### 换视频需要换 Cookie 吗

通常不用。只换视频链接即可。Cookie 过期或换平台时才需要更新。

### 本地视频会被复制一份吗

不会。程序直接读取原文件，只生成 MP3、字幕、截图和笔记，避免浪费磁盘。

### 为什么本地视频没有作者和简介

普通本地文件没有这些平台信息。笔记会明确显示未提供，不会让 AI 编造。

### 是否要安装环境

第一次使用需要。Skill 能带走规则和脚本，但不能把 Python、ffmpeg、Edge、Whisper 模型和你的登录 Cookie 全部塞进压缩包。
