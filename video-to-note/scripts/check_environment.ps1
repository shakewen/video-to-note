param(
    [string]$RuntimeRoot = $env:VIDEO_NOTE_HOME,
    [switch]$InstallPythonPackages
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

if (-not $RuntimeRoot) {
    $RuntimeRoot = if (Test-Path -LiteralPath "D:\") { "D:\VideoNoteRuntime" } else { Join-Path $HOME ".video-note-runtime" }
}
New-Item -ItemType Directory -Path (Join-Path $RuntimeRoot "cache\whisper") -Force | Out-Null

$python = Get-Command python -ErrorAction SilentlyContinue
if ($InstallPythonPackages) {
    if (-not $python) { throw "未找到 Python，无法安装 Python 依赖。" }
    & $python.Source -m pip install -U yt-dlp openai-whisper pillow
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$required = @("python", "yt-dlp", "ffmpeg", "ffprobe", "whisper", "msedge")
$status = foreach ($name in $required) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    [pscustomobject]@{ name = $name; available = [bool]$command; path = if ($command) { $command.Source } else { $null } }
}

[pscustomobject]@{
    status = if ($status.available -contains $false) { "missing_tools" } else { "ok" }
    runtime_root = $RuntimeRoot
    whisper_model_dir = (Join-Path $RuntimeRoot "cache\whisper")
    tools = $status
    optional = @(
        [pscustomobject]@{
            name = "npx"
            available = [bool](Get-Command npx -ErrorAction SilentlyContinue)
            purpose = "超长页面的 Playwright 分片截图；不影响核心笔记生成"
        }
    )
} | ConvertTo-Json -Depth 4

if ($status.available -contains $false) { exit 2 }
