@echo off
title ActivityWatch Sync - Using Environment Variables
echo ========================================
echo ActivityWatch Sync - Environment Variables
echo ========================================
echo.
echo Setting environment variables...
echo.

REM Set your credentials here or set them system-wide
set TIMESHEET_DEVELOPER_NAME=mrunali
set TIMESHEET_API_TOKEN=your-api-token-here

echo Developer: %TIMESHEET_DEVELOPER_NAME%
echo.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "sync_dynamic.ps1"
pause
