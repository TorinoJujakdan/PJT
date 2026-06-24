param(
    [string]$TaskName = "SmartFuelCardAIBatchIngestion",
    [string]$StartTime = "03:00",
    [switch]$EnableDailySchedule
)

$ErrorActionPreference = "Stop"

if (-not $EnableDailySchedule) {
    Write-Host "Card AI ingestion is manual/review-gated by default."
    Write-Host "Run backend/scripts/run_card_ai_ingestion.ps1 directly for an operator-reviewed batch."
    Write-Host "To intentionally register a daily Windows task, re-run with -EnableDailySchedule."
    return
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunnerPath = Resolve-Path (Join-Path $ScriptDir "run_card_ai_ingestion.ps1")
$BackendDir = Resolve-Path (Join-Path $ScriptDir "..")
$UserId = "$env:USERDOMAIN\$env:USERNAME"
$StartAt = [datetime]::ParseExact($StartTime, "HH:mm", [Globalization.CultureInfo]::InvariantCulture)

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RunnerPath`"" `
    -WorkingDirectory $BackendDir
$Trigger = New-ScheduledTaskTrigger -Daily -At $StartAt
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$Principal = New-ScheduledTaskPrincipal `
    -UserId $UserId `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Runs review-gated SmartFuel card AI ingestion into local SQLite." `
    -Force | Out-Null

Get-ScheduledTask -TaskName $TaskName
