@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo Starting SmartFuel local servers...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-smartfuel.ps1"

if errorlevel 1 (
  echo.
  echo SmartFuel server launcher failed.
  pause
)
