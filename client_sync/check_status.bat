@echo off
REM ============================================================
REM ActivityWatch Sync - Status Checker & Troubleshooter
REM ============================================================

setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo   ActivityWatch Sync - Status Checker
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "ISSUES_FOUND=0"

echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo       OK: %%i
) else (
    echo       ERROR: Python not found!
    set /a ISSUES_FOUND+=1
)

echo.
echo [2/6] Checking ActivityWatch...
curl -s http://localhost:5600/api/0/buckets/ >nul 2>&1
if %errorlevel% equ 0 (
    echo       OK: ActivityWatch is running on localhost:5600
) else (
    echo       ERROR: ActivityWatch is NOT running!
    echo              Please start ActivityWatch application.
    set /a ISSUES_FOUND+=1
)

echo.
echo [3/6] Checking configuration file...
if exist "%SCRIPT_DIR%\.env" (
    echo       OK: .env file exists
    findstr /C:"DEVELOPER_ID" "%SCRIPT_DIR%\.env" >nul 2>&1
    if %errorlevel% equ 0 (
        echo       OK: DEVELOPER_ID is configured
    ) else (
        echo       WARNING: DEVELOPER_ID may not be set in .env
    )
) else (
    echo       ERROR: .env file not found!
    echo              Run install_autostart.bat first.
    set /a ISSUES_FOUND+=1
)

echo.
echo [4/6] Checking if sync process is running...
set "SYNC_RUNNING=0"
for /f "tokens=*" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2^>nul ^| findstr /I "sync"') do (
    set "SYNC_RUNNING=1"
)
wmic process where "name='python.exe'" get commandline 2>nul | findstr /I "sync" >nul 2>&1
if %errorlevel% equ 0 (
    echo       OK: Sync process is RUNNING
    echo       (Look for system tray icon near your clock)
) else (
    wmic process where "name='pythonw.exe'" get commandline 2>nul | findstr /I "sync" >nul 2>&1
    if %errorlevel% equ 0 (
        echo       OK: Sync process is RUNNING (background)
    ) else (
        echo       WARNING: Sync process does NOT appear to be running
        echo                Run 'run_sync.bat' or 'start_visible.bat' to start
        set /a ISSUES_FOUND+=1
    )
)

echo.
echo [5/6] Checking auto-start configuration...
set "AUTOSTART_OK=0"

REM Check Startup folder
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ActivityWatch-Sync.vbs" (
    echo       OK: Startup folder entry exists
    set /a AUTOSTART_OK+=1
)

REM Check Registry
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ActivityWatchSync" >nul 2>&1
if %errorlevel% equ 0 (
    echo       OK: Registry auto-start entry exists
    set /a AUTOSTART_OK+=1
)

REM Check Scheduled Task
schtasks /query /tn "ActivityWatchSync-Logon" >nul 2>&1
if %errorlevel% equ 0 (
    echo       OK: Scheduled task exists
    set /a AUTOSTART_OK+=1
)

if %AUTOSTART_OK% equ 0 (
    echo       ERROR: No auto-start methods configured!
    echo              Run install_autostart.bat to set up.
    set /a ISSUES_FOUND+=1
)

echo.
echo [6/6] Checking recent log entries...
if exist "%SCRIPT_DIR%\sync_service.log" (
    echo       Recent log entries:
    echo       -------------------
    for /f "tokens=*" %%i in ('powershell -Command "Get-Content '%SCRIPT_DIR%\sync_service.log' -Tail 5"') do (
        echo       %%i
    )
) else if exist "%SCRIPT_DIR%\activitywatch_sync.log" (
    echo       Recent log entries:
    echo       -------------------
    for /f "tokens=*" %%i in ('powershell -Command "Get-Content '%SCRIPT_DIR%\activitywatch_sync.log' -Tail 5"') do (
        echo       %%i
    )
) else (
    echo       No log file found yet (sync may not have run)
)

echo.
echo ============================================================
if %ISSUES_FOUND% equ 0 (
    echo   STATUS: All checks passed! Sync should be working.
) else (
    echo   STATUS: Found %ISSUES_FOUND% issue(s). See above for details.
)
echo ============================================================
echo.

echo Options:
echo   [1] Start sync now (visible window)
echo   [2] Start sync now (background with tray icon)
echo   [3] View full log file
echo   [4] Re-run auto-start installer
echo   [5] Exit
echo.
set /p CHOICE="Enter choice (1-5): "

if "%CHOICE%"=="1" (
    start "" "%SCRIPT_DIR%\start_visible.bat"
) else if "%CHOICE%"=="2" (
    start "" wscript.exe "%SCRIPT_DIR%\hidden_launcher.vbs"
    echo Started! Look for the tray icon near your clock.
    timeout /t 3
) else if "%CHOICE%"=="3" (
    if exist "%SCRIPT_DIR%\sync_service.log" (
        notepad "%SCRIPT_DIR%\sync_service.log"
    ) else if exist "%SCRIPT_DIR%\activitywatch_sync.log" (
        notepad "%SCRIPT_DIR%\activitywatch_sync.log"
    ) else (
        echo No log file found.
        pause
    )
) else if "%CHOICE%"=="4" (
    call "%SCRIPT_DIR%\install_autostart.bat"
)

exit /b 0
