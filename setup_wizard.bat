@echo off
title Timesheet Sync - Setup Wizard
echo ========================================
echo    TIMESHEET SYNC SETUP WIZARD
echo ========================================
echo.
echo Welcome! This wizard will help you set up
echo the timesheet sync with your credentials.
echo.
pause

cls
echo ========================================
echo    STEP 1: CHECK CONNECTIVITY
echo ========================================
echo.
echo First, let's check if we can reach the server...
echo.
cd /d "%~dp0"
powershell -Command "try { $response = [System.Net.Dns]::GetHostAddresses('api-timesheet.firsteconomy.com'); Write-Host 'SUCCESS: Server is reachable!' -ForegroundColor Green; Write-Host ('IP: ' + $response[0].IPAddressToString) -ForegroundColor Gray } catch { Write-Host 'ERROR: Cannot reach server!' -ForegroundColor Red; Write-Host 'Make sure you are connected to company VPN or network.' -ForegroundColor Yellow }"
echo.
pause

cls
echo ========================================
echo    STEP 2: CHECK ACTIVITYWATCH
echo ========================================
echo.
echo Checking if ActivityWatch is running...
echo.
powershell -Command "try { Invoke-RestMethod -Uri 'http://localhost:5600/api/0/info' -TimeoutSec 5 | Out-Null; Write-Host 'SUCCESS: ActivityWatch is running!' -ForegroundColor Green } catch { Write-Host 'ERROR: ActivityWatch is not running!' -ForegroundColor Red; Write-Host 'Please start ActivityWatch before running sync.' -ForegroundColor Yellow }"
echo.
pause

cls
echo ========================================
echo    STEP 3: CONFIGURE CREDENTIALS
echo ========================================
echo.
echo Now let's set up your credentials...
echo.
echo Choose your preferred method:
echo.
echo 1. Secure Storage (Recommended) - Encrypted, persistent
echo 2. Config File - Easy to edit, less secure
echo 3. Manual Entry - Enter each time you run sync
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    echo.
    echo Setting up secure credentials...
    powershell -ExecutionPolicy Bypass -File "manage_credentials.ps1"
    set START_METHOD=start_sync_secure.bat
) else if "%choice%"=="2" (
    echo.
    echo Creating config file...
    set /p devname="Enter your developer name: "
    set /p apitoken="Enter your API token: "
    echo { > sync_config.json
    echo     "DeveloperName": "%devname%", >> sync_config.json
    echo     "ApiToken": "%apitoken%" >> sync_config.json
    echo } >> sync_config.json
    echo.
    echo Config file created!
    set START_METHOD=start_sync_interactive.bat
) else (
    echo.
    echo You chose manual entry mode.
    set START_METHOD=start_sync_interactive.bat
)

cls
echo ========================================
echo    SETUP COMPLETE!
echo ========================================
echo.
echo Your timesheet sync is now configured!
echo.
echo To start syncing, run:
echo    %START_METHOD%
echo.
echo Or you can create a desktop shortcut to:
echo    %~dp0%START_METHOD%
echo.
echo Additional options:
echo - manage_credentials.bat   : Manage secure credentials
echo - diagnose_connection.bat  : Troubleshoot connection issues
echo - README_DYNAMIC_CONFIG.md : Detailed documentation
echo.
echo Would you like to start syncing now?
set /p startnow="Enter Y to start, N to exit (Y/N): "

if /i "%startnow%"=="Y" (
    echo.
    echo Starting sync...
    call "%START_METHOD%"
) else (
    echo.
    echo Setup completed. Run %START_METHOD% when ready.
)

pause
