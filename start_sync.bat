@echo off
title ActivityWatch Sync - ankita gholap
echo Starting ActivityWatch sync for ankita gholap...
echo Using PowerShell (no Python installation needed)
echo.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "sync.ps1"
pause