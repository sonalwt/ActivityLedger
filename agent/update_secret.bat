@echo off
setlocal enabledelayedexpansion

set "AGENT_DIR=%~dp0"
set "AGENT_DIR=%AGENT_DIR:~0,-1%"
set "CONFIG_FILE=%AGENT_DIR%\config.json"
set "MASTER_SECRET=TimesheetMaster2025258c362c"
set "SERVER_URL=https://api-timesheet.firsteconomy.com/api/v1/activitywatch/webhook"

echo ============================================
echo   ActivityLedger Agent - Setup ^& Sync Fix
echo ============================================
echo.

:: Check config exists
if not exist "%CONFIG_FILE%" (
    echo ERROR: config.json not found at %CONFIG_FILE%
    pause
    exit /b 1
)

:: Update config using PowerShell
echo [1/2] Updating config.json...
powershell -command ^
    "$c = Get-Content '%CONFIG_FILE%' | ConvertFrom-Json; ^
     $c.master_secret = '%MASTER_SECRET%'; ^
     $c.server_url = '%SERVER_URL%'; ^
     $c | ConvertTo-Json -Depth 10 | Set-Content '%CONFIG_FILE%'; ^
     Write-Host '  master_secret -> updated'; ^
     Write-Host '  server_url    -> updated'; ^
     Write-Host ('  developer_id  -> ' + $c.developer_id)"

:: Also update config in Startup folder
set "STARTUP_CONFIG=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\config.json"
if exist "%STARTUP_CONFIG%" (
    powershell -command ^
        "$c = Get-Content '%STARTUP_CONFIG%' | ConvertFrom-Json; ^
         $c.master_secret = '%MASTER_SECRET%'; ^
         $c.server_url = '%SERVER_URL%'; ^
         $c | ConvertTo-Json -Depth 10 | Set-Content '%STARTUP_CONFIG%'"
    echo   Startup folder config updated too.
)

:: Restart agent
echo [2/2] Restarting agent...
taskkill /F /IM ActivityLedgerAgent.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

:: Start from Startup folder if exists, else from agent dir
set "STARTUP_EXE=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ActivityLedgerAgent.exe"
if exist "%STARTUP_EXE%" (
    start "" "%STARTUP_EXE%"
    echo   Agent restarted from Startup folder.
) else if exist "%AGENT_DIR%\ActivityLedgerAgent.exe" (
    start "" "%AGENT_DIR%\ActivityLedgerAgent.exe"
    echo   Agent restarted from agent folder.
) else (
    echo   WARNING: ActivityLedgerAgent.exe not found. Start it manually.
)

echo.
echo ============================================
echo   Done! Data will sync every 5 minutes.
echo ============================================
echo.
pause
