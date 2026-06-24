$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Resolve-Path (Join-Path $ScriptDir "..")
$ProjectDir = Resolve-Path (Join-Path $BackendDir "..")
$PythonPath = Join-Path $ProjectDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python executable not found: $PythonPath"
}

$LogDir = Join-Path $BackendDir "logs\card-ai-ingestion"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $LogDir "run-$Timestamp.log"
$Limit = if ($env:CARD_AI_BATCH_LIMIT) { [int]$env:CARD_AI_BATCH_LIMIT } else { 10 }
$ScrollCount = if ($env:CARD_AI_BATCH_SCROLL_COUNT) { [int]$env:CARD_AI_BATCH_SCROLL_COUNT } else { 4 }
$Normalizer = if ($env:CARD_AI_BATCH_NORMALIZER) { "$env:CARD_AI_BATCH_NORMALIZER" } else { "gms" }
$TruthyValues = @("1", "true", "yes", "y", "on")

$CommandArgs = @(
    "manage.py",
    "ingest_card_search_ai",
    "--normalizer=$Normalizer",
    "--detail",
    "--limit=$Limit",
    "--scroll-count=$ScrollCount"
)

if ($TruthyValues -contains [string]::Copy("$env:CARD_AI_BATCH_FORCE").ToLowerInvariant()) {
    $CommandArgs += "--force"
}

if ($TruthyValues -contains [string]::Copy("$env:CARD_AI_BATCH_DRY_RUN").ToLowerInvariant()) {
    $CommandArgs += "--dry-run"
}

Push-Location $BackendDir
try {
    "[$(Get-Date -Format o)] Starting SmartFuel card AI ingestion" | Tee-Object -FilePath $LogFile -Append
    "Command: $PythonPath $($CommandArgs -join ' ')" | Tee-Object -FilePath $LogFile -Append
    $StdOutFile = [IO.Path]::GetTempFileName()
    $StdErrFile = [IO.Path]::GetTempFileName()
    try {
        $Process = Start-Process `
            -FilePath $PythonPath `
            -ArgumentList $CommandArgs `
            -WorkingDirectory $BackendDir `
            -Wait `
            -PassThru `
            -NoNewWindow `
            -RedirectStandardOutput $StdOutFile `
            -RedirectStandardError $StdErrFile
        Get-Content -LiteralPath $StdOutFile | Tee-Object -FilePath $LogFile -Append
        Get-Content -LiteralPath $StdErrFile | Tee-Object -FilePath $LogFile -Append
        $ExitCode = $Process.ExitCode
    } finally {
        Remove-Item -LiteralPath $StdOutFile -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $StdErrFile -Force -ErrorAction SilentlyContinue
    }
    "[$(Get-Date -Format o)] ExitCode=$ExitCode" | Tee-Object -FilePath $LogFile -Append
    if ($ExitCode -ne 0) {
        throw "Card AI ingestion failed with exit code $ExitCode. Log: $LogFile"
    }
} finally {
    Pop-Location
}
