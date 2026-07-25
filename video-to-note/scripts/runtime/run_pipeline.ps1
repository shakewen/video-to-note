$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

$Python = if ($env:VIDEO_NOTE_PYTHON) { $env:VIDEO_NOTE_PYTHON } else { "python" }
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = $PSScriptRoot
& $Python -m video_note_pipeline.cli @args
exit $LASTEXITCODE
