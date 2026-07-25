param(
    [string]$RuntimeRoot = $env:VIDEO_NOTE_HOME,
    [switch]$InstallPythonPackages
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

if (-not $RuntimeRoot) {
    $RuntimeRoot = Join-Path (Get-Location).Path ".video-note-runtime"
}
$RuntimeRoot = [System.IO.Path]::GetFullPath($RuntimeRoot)
$taskRuntimePath = Join-Path (Split-Path -Parent $RuntimeRoot) "task-runtime.ps1"
$taskRuntimeLoaded = $false
if (Test-Path -LiteralPath $taskRuntimePath -PathType Leaf) {
    . $taskRuntimePath
    $taskRuntimeLoaded = $true
    if ($env:VIDEO_NOTE_HOME) {
        $RuntimeRoot = [System.IO.Path]::GetFullPath($env:VIDEO_NOTE_HOME)
    }
}
New-Item -ItemType Directory -Path (Join-Path $RuntimeRoot "cache\whisper") -Force | Out-Null

function Find-VideoNoteFiles {
    param(
        [string]$Root,
        [Parameter(Mandatory = $true)][string]$Filter
    )

    if (-not $Root -or -not (Test-Path -LiteralPath $Root -PathType Container)) {
        return @()
    }
    return @(
        Get-ChildItem -LiteralPath $Root -Filter $Filter -File -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName |
            ForEach-Object { $_.FullName }
    )
}

function Resolve-VideoNoteTool {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$EnvironmentName,
        [string[]]$FallbackNames = @(),
        [string[]]$WorkspaceCandidates = @(),
        [string[]]$SystemCandidates = @()
    )

    $configuredPath = [Environment]::GetEnvironmentVariable($EnvironmentName)
    if ($configuredPath) {
        if (Test-Path -LiteralPath $configuredPath -PathType Leaf) {
            return [pscustomobject]@{
                name = $Name
                available = $true
                path = (Get-Item -LiteralPath $configuredPath).FullName
                resolution = "explicit_path"
                detail = $null
            }
        }
        return [pscustomobject]@{
            name = $Name
            available = $false
            path = $configuredPath
            resolution = "invalid_explicit_path"
            detail = "$EnvironmentName points to a missing file"
        }
    }

    foreach ($candidate in $WorkspaceCandidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return [pscustomobject]@{
                name = $Name
                available = $true
                path = (Get-Item -LiteralPath $candidate).FullName
                resolution = "workspace_runtime"
                detail = $null
            }
        }
    }

    foreach ($candidate in @($Name) + $FallbackNames) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            return [pscustomobject]@{
                name = $Name
                available = $true
                path = $command.Source
                resolution = "path"
                detail = $null
            }
        }
    }

    foreach ($candidate in $SystemCandidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return [pscustomobject]@{
                name = $Name
                available = $true
                path = (Get-Item -LiteralPath $candidate).FullName
                resolution = "system_common"
                detail = $null
            }
        }
    }

    return [pscustomobject]@{
        name = $Name
        available = $false
        path = $null
        resolution = "not_resolved"
        detail = "The tool was not found in explicit paths, workspace runtime, PATH, or Windows common locations"
    }
}

function Test-PythonModule {
    param(
        [Parameter(Mandatory = $true)][string]$PythonPath,
        [Parameter(Mandatory = $true)][string]$ModuleName
    )

    & $PythonPath -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('$ModuleName') else 1)" 2>$null
    return $LASTEXITCODE -eq 0
}

$workspacePythonCandidates = @(
    (Join-Path $RuntimeRoot "venv\Scripts\python.exe"),
    (Join-Path $RuntimeRoot "python\python.exe"),
    (Join-Path $RuntimeRoot "python.exe")
)
$workspaceYtDlpCandidates = @(
    (Join-Path $RuntimeRoot "venv\Scripts\yt-dlp.exe"),
    (Join-Path $RuntimeRoot "yt-dlp.exe")
)
$workspaceFfmpegCandidates = Find-VideoNoteFiles -Root $RuntimeRoot -Filter "ffmpeg.exe"
$workspaceFfprobeCandidates = Find-VideoNoteFiles -Root $RuntimeRoot -Filter "ffprobe.exe"
$workspaceBrowserCandidates = @(
    (Find-VideoNoteFiles -Root $RuntimeRoot -Filter "msedge.exe"),
    (Find-VideoNoteFiles -Root $RuntimeRoot -Filter "chrome.exe")
)
$workspaceWhisperCandidates = @(
    (Join-Path $RuntimeRoot "venv\Scripts\whisper.exe"),
    (Join-Path $RuntimeRoot "whisper.exe")
)

$localAppData = [Environment]::GetFolderPath("LocalApplicationData")
$systemPythonCandidates = @()
$systemYtDlpCandidates = @()
$pythonInstallRoot = if ($localAppData) { Join-Path $localAppData "Programs\Python" } else { $null }
if ($pythonInstallRoot -and (Test-Path -LiteralPath $pythonInstallRoot -PathType Container)) {
    $pythonDirectories = @(
        Get-ChildItem -LiteralPath $pythonInstallRoot -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "Python*" } |
            Sort-Object Name -Descending
    )
    foreach ($directory in $pythonDirectories) {
        $systemPythonCandidates += Join-Path $directory.FullName "python.exe"
        $systemYtDlpCandidates += Join-Path $directory.FullName "Scripts\yt-dlp.exe"
    }
}

$winGetPackagesRoot = if ($localAppData) { Join-Path $localAppData "Microsoft\WinGet\Packages" } else { $null }
$systemFfmpegCandidates = @()
$systemFfprobeCandidates = @()
if ($winGetPackagesRoot -and (Test-Path -LiteralPath $winGetPackagesRoot -PathType Container)) {
    $ffmpegPackageDirectories = @(
        Get-ChildItem -LiteralPath $winGetPackagesRoot -Directory -Filter "Gyan.FFmpeg*" -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending
    )
    foreach ($directory in $ffmpegPackageDirectories) {
        $systemFfmpegCandidates += Find-VideoNoteFiles -Root $directory.FullName -Filter "ffmpeg.exe"
        $systemFfprobeCandidates += Find-VideoNoteFiles -Root $directory.FullName -Filter "ffprobe.exe"
    }
}

$programFiles = [Environment]::GetFolderPath("ProgramFiles")
$programFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
$systemBrowserCandidates = @()
if ($programFilesX86) {
    $systemBrowserCandidates += Join-Path $programFilesX86 "Microsoft\Edge\Application\msedge.exe"
    $systemBrowserCandidates += Join-Path $programFilesX86 "Google\Chrome\Application\chrome.exe"
}
if ($programFiles) {
    $systemBrowserCandidates += Join-Path $programFiles "Microsoft\Edge\Application\msedge.exe"
    $systemBrowserCandidates += Join-Path $programFiles "Google\Chrome\Application\chrome.exe"
}

$python = Resolve-VideoNoteTool `
    -Name "python" `
    -EnvironmentName "VIDEO_NOTE_PYTHON" `
    -WorkspaceCandidates $workspacePythonCandidates `
    -SystemCandidates $systemPythonCandidates
$ytDlp = Resolve-VideoNoteTool `
    -Name "yt-dlp" `
    -EnvironmentName "VIDEO_NOTE_YT_DLP" `
    -WorkspaceCandidates $workspaceYtDlpCandidates `
    -SystemCandidates $systemYtDlpCandidates
$ffmpeg = Resolve-VideoNoteTool `
    -Name "ffmpeg" `
    -EnvironmentName "VIDEO_NOTE_FFMPEG" `
    -WorkspaceCandidates $workspaceFfmpegCandidates `
    -SystemCandidates $systemFfmpegCandidates
$ffprobe = Resolve-VideoNoteTool `
    -Name "ffprobe" `
    -EnvironmentName "VIDEO_NOTE_FFPROBE" `
    -WorkspaceCandidates $workspaceFfprobeCandidates `
    -SystemCandidates $systemFfprobeCandidates
$browser = Resolve-VideoNoteTool `
    -Name "browser" `
    -EnvironmentName "VIDEO_NOTE_BROWSER" `
    -FallbackNames @("msedge", "chrome") `
    -WorkspaceCandidates $workspaceBrowserCandidates `
    -SystemCandidates $systemBrowserCandidates

if ($InstallPythonPackages) {
    if (-not $python.available) { throw "Python is required to install Python packages." }
    $requestedBackend = if ($env:VIDEO_NOTE_TRANSCRIBE_BACKEND) { $env:VIDEO_NOTE_TRANSCRIBE_BACKEND } else { "faster-whisper" }
    $transcribePackage = if ($requestedBackend -eq "openai-whisper") { "openai-whisper" } else { "faster-whisper" }
    & $python.path -m pip install -U yt-dlp pillow $transcribePackage
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$requestedBackend = if ($env:VIDEO_NOTE_TRANSCRIBE_BACKEND) {
    $env:VIDEO_NOTE_TRANSCRIBE_BACKEND.Trim().ToLowerInvariant()
} else {
    "auto"
}
$whisperCommand = Resolve-VideoNoteTool `
    -Name "whisper" `
    -EnvironmentName "VIDEO_NOTE_WHISPER" `
    -WorkspaceCandidates $workspaceWhisperCandidates
$fasterWhisperAvailable = $python.available -and (Test-PythonModule -PythonPath $python.path -ModuleName "faster_whisper")

if ($requestedBackend -in @("faster-whisper", "faster_whisper")) {
    $transcriptionBackend = "faster-whisper"
    $transcriberAvailable = $fasterWhisperAvailable
    $transcriberPath = if ($fasterWhisperAvailable) { $python.path } else { $null }
    $transcriberDetail = if ($fasterWhisperAvailable) { "Python module faster_whisper is available" } else { "The resolved Python is missing faster_whisper" }
} elseif ($requestedBackend -eq "openai-whisper") {
    $transcriptionBackend = "openai-whisper"
    $transcriberAvailable = $whisperCommand.available
    $transcriberPath = $whisperCommand.path
    $transcriberDetail = if ($whisperCommand.available) { "whisper CLI is available" } else { "The whisper CLI is missing" }
} elseif ($requestedBackend -eq "auto") {
    if ($fasterWhisperAvailable) {
        $transcriptionBackend = "faster-whisper"
        $transcriberAvailable = $true
        $transcriberPath = $python.path
        $transcriberDetail = "Automatically selected Python module faster_whisper"
    } else {
        $transcriptionBackend = "openai-whisper"
        $transcriberAvailable = $whisperCommand.available
        $transcriberPath = $whisperCommand.path
        $transcriberDetail = if ($whisperCommand.available) { "Automatically selected whisper CLI" } else { "No supported transcription backend was found" }
    }
} else {
    $transcriptionBackend = $requestedBackend
    $transcriberAvailable = $false
    $transcriberPath = $null
    $transcriberDetail = "VIDEO_NOTE_TRANSCRIBE_BACKEND supports auto, faster-whisper, or openai-whisper"
}

$transcriber = [pscustomobject]@{
    name = "transcriber"
    available = $transcriberAvailable
    path = $transcriberPath
    resolution = $transcriptionBackend
    detail = $transcriberDetail
}
$status = @($python, $ytDlp, $ffmpeg, $ffprobe, $browser, $transcriber)
$missingTools = @($status | Where-Object { -not $_.available })
$environmentReady = $missingTools.Count -eq 0
$guidance = if ($environmentReady) {
    @("Reuse the resolved paths and continue without installing or downloading dependencies.")
} else {
    @(
        "Ask the user for authorization before downloading any missing dependency.",
        "Download or install missing dependencies only inside the workspace runtime: $RuntimeRoot",
        "Do not use system-wide installers, do not modify the system PATH, and do not install globally.",
        "After a timeout, inspect existing files and processes before any retry."
    )
}

[pscustomobject]@{
    status = if ($environmentReady) { "ok" } else { "missing_tools" }
    next_action = if ($environmentReady) { "continue" } else { "guide_workspace_install" }
    runtime_root = $RuntimeRoot
    task_runtime = [pscustomobject]@{
        loaded = $taskRuntimeLoaded
        path = if ($taskRuntimeLoaded) { $taskRuntimePath } else { $null }
    }
    workspace_runtime_dir = $RuntimeRoot
    whisper_model_dir = (Join-Path $RuntimeRoot "cache\whisper")
    transcription_backend = $transcriptionBackend
    tools = $status
    missing_tools = $missingTools
    guidance = $guidance
    optional = @(
        [pscustomobject]@{
            name = "npx"
            available = [bool](Get-Command npx -ErrorAction SilentlyContinue)
            purpose = "Optional Playwright support for very long page screenshots"
        }
    )
} | ConvertTo-Json -Depth 6

if (-not $environmentReady) { exit 2 }
