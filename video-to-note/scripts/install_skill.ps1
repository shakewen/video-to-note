param(
    [ValidateSet("Codex", "Claude", "Copilot", "Gemini", "Both", "All", "Custom")]
    [string]$Agent = "Both",
    [string]$ClaudeProjectRoot = "",
    [string]$ProfileRoot = "",
    [string[]]$TargetSkillsRoot = @()
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$skillRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$homeRoot = if ($ProfileRoot) { [IO.Path]::GetFullPath($ProfileRoot) } else { $HOME }
$selectedAgents = switch ($Agent) {
    "Both" { @("Codex", "Claude") }
    "All" { @("Codex", "Claude", "Copilot", "Gemini") }
    "Custom" { @() }
    default { @($Agent) }
}

$destinations = @()
if ($selectedAgents -contains "Codex") {
    $codexHome = if ($ProfileRoot) {
        Join-Path $homeRoot ".codex"
    } elseif ($env:CODEX_HOME) {
        $env:CODEX_HOME
    } else {
        Join-Path $homeRoot ".codex"
    }
    $destinations += Join-Path $codexHome "skills\video-to-note"
}
if ($selectedAgents -contains "Claude") {
    $claudeBase = if ($ClaudeProjectRoot) {
        Join-Path ([IO.Path]::GetFullPath($ClaudeProjectRoot)) ".claude\skills"
    } else {
        Join-Path $homeRoot ".claude\skills"
    }
    $destinations += Join-Path $claudeBase "video-to-note"
}
if ($selectedAgents -contains "Copilot") {
    $destinations += Join-Path $homeRoot ".copilot\skills\video-to-note"
}
if ($selectedAgents -contains "Gemini") {
    $destinations += Join-Path $homeRoot ".gemini\skills\video-to-note"
}
foreach ($skillsRoot in $TargetSkillsRoot) {
    if (-not $skillsRoot) { continue }
    $destinations += Join-Path ([IO.Path]::GetFullPath($skillsRoot)) "video-to-note"
}

$destinations = @($destinations | Select-Object -Unique)
if ($destinations.Count -eq 0) {
    throw "No installation destination selected. Use -Agent Codex/Claude/Copilot/Gemini/All or provide -TargetSkillsRoot."
}

foreach ($destination in $destinations) {
    $target = [IO.Path]::GetFullPath($destination)
    if ($target -eq $skillRoot) { continue }
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $skillRoot "SKILL.md") -Destination $target -Force
    foreach ($folder in @("agents", "assets", "references", "scripts")) {
        $source = Join-Path $skillRoot $folder
        if (-not (Test-Path -LiteralPath $source)) { continue }
        $folderTarget = Join-Path $target $folder
        New-Item -ItemType Directory -Path $folderTarget -Force | Out-Null
        Get-ChildItem -LiteralPath $source -File -Recurse -Force |
            Where-Object { $_.Extension -ne ".pyc" -and $_.FullName -notmatch "[\\/]__pycache__[\\/]" } |
            ForEach-Object {
                $relativePath = $_.FullName.Substring($source.Length + 1)
                $fileTarget = Join-Path $folderTarget $relativePath
                $fileTargetDirectory = Split-Path -Parent $fileTarget
                New-Item -ItemType Directory -Path $fileTargetDirectory -Force | Out-Null
                Copy-Item -LiteralPath $_.FullName -Destination $fileTarget -Force
            }
    }
    Write-Output "installed: $target"
}
