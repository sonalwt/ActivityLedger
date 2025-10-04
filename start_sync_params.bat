@echo off
title ActivityWatch Sync - Command Line Parameters
echo ========================================
echo ActivityWatch Sync - With Parameters
echo ========================================
echo.
echo Usage: %~nx0 "DeveloperName" "ApiToken"
echo.

if "%~1"=="" (
    echo ERROR: Developer name not provided!
    echo.
    echo Example: %~nx0 "john.doe" "your-api-token"
    pause
    exit /b 1
)

if "%~2"=="" (
    echo ERROR: API token not provided!
    echo.
    echo Example: %~nx0 "john.doe" "your-api-token"
    pause
    exit /b 1
)

echo Starting sync for: %~1
echo.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "sync_dynamic.ps1" -DeveloperName "%~1" -ApiToken "%~2"
pause
