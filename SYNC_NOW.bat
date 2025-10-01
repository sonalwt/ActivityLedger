@echo off
title ActivityWatch Sync Launcher
cls
echo ======================================
echo  ACTIVITYWATCH SYNC - AUTO LAUNCHER
echo ======================================
echo.
echo Detecting best sync method...
echo.

REM Check if sync.ps1 exists
if exist "sync.ps1" (
    echo [OK] Found sync.ps1
    echo.
    echo Starting sync with HTTP endpoint...
    echo This avoids the 308 redirect issue.
    echo.
    powershell -ExecutionPolicy Bypass -File "sync.ps1"
) else (
    echo [ERROR] sync.ps1 not found!
    echo.
    echo Please ensure you're in the correct directory:
    echo E:\timesheet\timesheet_new
    echo.
    pause
    exit /b 1
)

pause