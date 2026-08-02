param(
    [Parameter(Mandatory = $true)][Alias("Url")][string]$Source,
    [Parameter(Mandatory = $true)][ValidateSet("ui_demo", "lecture", "interview", "mixed")][string]$VideoType,
    [Parameter(Mandatory = $true)][string]$ContentDescription,
    [ValidateSet("zh", "en", "mixed")][string]$Language = "zh",
    [ValidateSet("reference-warm", "calm-blue", "clean-gray")][string]$Theme = "reference-warm",
    [ValidateSet("source-faithful")][string]$NoteMode = "source-faithful",
    [string]$CookiesDirectory = ".\cookies",
    [string]$Workspace = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$workspacePath = [IO.Path]::GetFullPath($Workspace)
$runner = Join-Path $PSScriptRoot "runtime\run_pipeline.ps1"
$resolvedOutput = & $runner resolve-source $Source --cwd $workspacePath 2>&1
if ($LASTEXITCODE -ne 0) {
    throw ($resolvedOutput -join [Environment]::NewLine)
}
$resolved = ($resolvedOutput -join [Environment]::NewLine) | ConvertFrom-Json
$videoId = [string]$resolved.source_key
$outputRoot = Join-Path $workspacePath "outputs\$videoId"
foreach ($relative in @("metadata", "media", "transcript", "evidence", "html\frames", "render-check")) {
    New-Item -ItemType Directory -Path (Join-Path $outputRoot $relative) -Force | Out-Null
}

function ConvertTo-YamlString([string]$Value) {
    return $Value.Replace("\", "\\").Replace('"', '\"')
}

$cookieMode = "none"
$cookiePath = ""
if ($resolved.source_kind -eq "online_url") {
    $cookieMode = "optional_file"
    $cookiePath = (Join-Path $CookiesDirectory "$($resolved.platform).txt").Replace("\", "/")
}

$configPath = Join-Path $workspacePath "video-request.yaml"
$config = @"
note_request:
  video_source: "$(ConvertTo-YamlString $Source)"
  video_type_and_content: "$(ConvertTo-YamlString $ContentDescription)"
  color_and_layout: "$Theme"
video:
  url: "$(ConvertTo-YamlString ([string]$resolved.input_value))"
  platform: "$($resolved.platform)"
  source_kind: "$($resolved.source_kind)"
  source_id: "$($resolved.source_id)"
  expected_id: "$videoId"
  is_playlist_or_multipart: false
  parts_to_process: "single"
cookies:
  mode: "$cookieMode"
  file_path: "$(ConvertTo-YamlString $cookiePath)"
language:
  primary: "$Language"
  whisper_model_for_zh: "turbo"
  whisper_model_for_en: "small.en"
  translate_english_to_chinese: true
  keep_key_english_quotes: true
frames:
  required_for_ui_or_operation_video: true
  video_type: "$VideoType"
note:
  mode: "$NoteMode"
output:
  root_dir: "./outputs"
  preferred_name: ""
  final_html_name: "index.html"
  quality_report_name: "quality_report.md"
"@
[IO.File]::WriteAllText($configPath, $config, [Text.UTF8Encoding]::new($false))

[pscustomobject]@{
    status = "ok"
    platform = $resolved.platform
    source_kind = $resolved.source_kind
    source_id = $resolved.source_id
    video_id = $videoId
    config = $configPath
    output_root = $outputRoot
    cookie_path = if ($cookiePath) { $cookiePath } else { $null }
    theme = $Theme
} | ConvertTo-Json -Compress
