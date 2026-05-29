$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$PythonExe = Join-Path $Root ".venv\Scripts\python.exe"
$UvicornExe = Join-Path $Root ".venv\Scripts\uvicorn.exe"

function Assert-PathExists {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Message`nMissing: $Path"
    }
}

function Start-ServiceWindow {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$Command
    )

    $WindowScript = @"
`$Host.UI.RawUI.WindowTitle = "$Title"
chcp 65001 | Out-Null
Write-Host "[$Title] starting..." -ForegroundColor Cyan
Set-Location -LiteralPath "$WorkingDirectory"
$Command
"@

    $EncodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($WindowScript))

    Start-Process powershell.exe -WorkingDirectory $WorkingDirectory -ArgumentList @(
        "-NoProfile",
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", $EncodedCommand
    ) | Out-Null
}

function Test-PortListening {
    param([Parameter(Mandatory = $true)][int]$Port)

    $Connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1

    return $null -ne $Connection
}

try {
    Assert-PathExists -Path $BackendDir -Message "backend folder was not found."
    Assert-PathExists -Path $FrontendDir -Message "frontend folder was not found."
    Assert-PathExists -Path $PythonExe -Message "Python virtual environment was not found. Create .venv first."
    Assert-PathExists -Path $UvicornExe -Message "uvicorn was not found in .venv. Install backend requirements first."
    Assert-PathExists -Path (Join-Path $FrontendDir "node_modules\.bin\vite.cmd") -Message "frontend node_modules was not found. Run npm install in frontend first."

    Write-Host "Starting SmartFuel local servers..." -ForegroundColor Green

    if (Test-PortListening -Port 8000) {
        Write-Host "Backend is already running on 127.0.0.1:8000" -ForegroundColor Yellow
    }
    else {
        Start-ServiceWindow `
            -Title "SmartFuel Backend - Django 8000" `
            -WorkingDirectory $BackendDir `
            -Command "& `"$PythonExe`" manage.py runserver 127.0.0.1:8000"
    }

    if (Test-PortListening -Port 8001) {
        Write-Host "Search API is already running on 127.0.0.1:8001" -ForegroundColor Yellow
    }
    else {
        Start-ServiceWindow `
            -Title "SmartFuel Search API - FastAPI 8001" `
            -WorkingDirectory $BackendDir `
            -Command "& `"$UvicornExe`" search_api.main:app --host 127.0.0.1 --port 8001 --reload"
    }

    if (Test-PortListening -Port 5173) {
        Write-Host "Frontend is already running on 127.0.0.1:5173" -ForegroundColor Yellow
    }
    else {
        Start-ServiceWindow `
            -Title "SmartFuel Frontend - Vite 5173" `
            -WorkingDirectory $FrontendDir `
            -Command "npm.cmd run dev"
    }

    Start-Sleep -Seconds 3
    Start-Process "http://127.0.0.1:5173" | Out-Null

    Write-Host ""
    Write-Host "SmartFuel servers were launched in separate windows." -ForegroundColor Green
    Write-Host "Frontend:   http://127.0.0.1:5173"
    Write-Host "Backend:    http://127.0.0.1:8000"
    Write-Host "Search API: http://127.0.0.1:8001/search-api/health/"
    Write-Host ""
    Write-Host "Close each server window, or press Ctrl+C inside it, to stop that server."
}
catch {
    Write-Host ""
    Write-Host "Failed to start SmartFuel servers." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to close"
    exit 1
}
