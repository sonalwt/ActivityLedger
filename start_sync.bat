REM Run the PowerShell sync script
powershell -ExecutionPolicy Bypass -File "sync.ps1"
pause

@echo off
title ActivityWatch Sync - Windows
echo Starting ActivityWatch sync...
echo Using PowerShell (no Python needed)
echo.

cd /d "%~dp0"

powershell -ExecutionPolicy Bypass -File "sync.ps1"

pause
