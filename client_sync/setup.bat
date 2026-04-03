@echo off
setlocal EnableDelayedExpansion
REM ============================================================
REM ActivityWatch Sync - ONE-CLICK SETUP
REM Works on ANY Windows PC (No Python needed!)
REM ============================================================

echo.
echo ============================================================
echo   ActivityWatch Sync - One-Click Setup
echo   Works on ANY Windows PC!
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "CONFIG_FILE=%SCRIPT_DIR%\sync_config.txt"

REM Check if already configured
if exist "%CONFIG_FILE%" (
    for /f "tokens=1,2 delims==" %%a in (%CONFIG_FILE%) do (
        if "%%a"=="DEVELOPER_ID" set "DEV_ID=%%b"
        if "%%a"=="API_TOKEN" set "DEV_TOKEN=%%b"
    )
    echo Found existing config:
    echo   Developer ID: !DEV_ID!
    echo.
    set /p RECONFIG="Reconfigure? (Y/N): "
    if /i not "!RECONFIG!"=="Y" goto :skip_config
)

:get_config
echo.
echo Enter your credentials (from your admin or registration):
echo.
set /p DEV_ID="Developer ID (your name in database): "
set /p DEV_TOKEN="API Token: "

REM Save config
(
echo DEVELOPER_ID=%DEV_ID%
echo API_TOKEN=%DEV_TOKEN%
) > "%CONFIG_FILE%"

echo.
echo [OK] Configuration saved!

:skip_config
echo.

REM Install VS Code ActivityWatch extension (if VS Code is installed)
echo [1/5] Installing VS Code ActivityWatch extension...
where code >nul 2>&1
if !errorlevel! equ 0 (
    code --install-extension activitywatch.aw-watcher-vscode --force >nul 2>&1
    if !errorlevel! equ 0 (
        echo       Done! aw-watcher-vscode installed
    ) else (
        echo       [WARN] Could not install. Install manually from VS Code Extensions.
    )
) else (
    echo       [SKIP] VS Code not found. Install aw-watcher-vscode manually.
)
echo.

REM Install Chrome ActivityWatch extension
echo [2/5] ActivityWatch Browser Extension...
echo       Opening Chrome Web Store - click "Add to Chrome" to install.
start "" "https://chromewebstore.google.com/detail/activitywatch-web-watcher/nglaklhklhcoonedhgnpgddginnjdadi"
echo       Done! Chrome Web Store opened.
echo.
timeout /t 3 >nul

REM Create VBS launcher (runs PowerShell hidden)
echo [3/5] Creating launcher...
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%SCRIPT_DIR%"
echo WshShell.Run "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File ""%SCRIPT_DIR%\sync_service.ps1""", 0, False
) > "%SCRIPT_DIR%\run_sync.vbs"
echo       Done!

REM Add to Windows Startup
echo [4/5] Adding to Windows startup...
copy /Y "%SCRIPT_DIR%\run_sync.vbs" "%STARTUP%\ActivityWatch-Sync.vbs" >nul 2>&1
echo       Done!

REM Start now
echo [5/5] Starting sync service...
start "" wscript.exe "%SCRIPT_DIR%\run_sync.vbs"
echo       Done!

echo.
echo ============================================================
echo   SETUP COMPLETE!
echo ============================================================
echo.
echo What happens now:
echo   [OK] Syncs your activity every 5 minutes
echo   [OK] Starts automatically when Windows boots
echo   [OK] Runs silently in background
echo.
echo Extensions:
echo   [OK] aw-watcher-vscode: Tracks code project, file, language
echo   [OK] aw-watcher-web:    Tracks browser URLs and domains
echo.
echo Requirements (must be installed):
echo   - ActivityWatch (https://activitywatch.net)
echo.
echo ============================================================
echo.
pause
