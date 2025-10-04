@echo off
title ActivityWatch Sync - Dynamic Configuration
echo ========================================
echo ActivityWatch Sync - Interactive Mode
echo ========================================
echo.
echo This will prompt you for developer name and API token
echo.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "sync_dynamic.ps1"
pause
