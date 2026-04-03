@echo off
REM ============================================================
REM ActivityWatch Auto-Sync - One-Click Installer
REM Just double-click this file - no configuration needed!
REM ============================================================

setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo   ActivityWatch Auto-Sync Installer
echo   One-click setup - No configuration needed!
echo ============================================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo.
    echo Please install Python from: https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Install dependencies
echo [STEP 1/6] Installing dependencies...
pip install requests pystray pillow -q 2>nul
echo [OK] Dependencies installed
echo.

REM Create hidden launcher
echo [STEP 2/6] Setting up auto-start...

REM Get Python path
for /f "tokens=*" %%i in ('where python') do set "PYTHON_PATH=%%i" & goto :found_python
:found_python

REM Create VBS launcher for hidden execution
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%SCRIPT_DIR%"
echo WshShell.Run """%PYTHON_PATH%"" ""%SCRIPT_DIR%\auto_sync_service.py"" --hidden", 0, False
) > "%SCRIPT_DIR%\run_hidden.vbs"

REM Add to Startup folder
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
copy /Y "%SCRIPT_DIR%\run_hidden.vbs" "%STARTUP%\ActivityWatch-AutoSync.vbs" >nul 2>&1
echo [OK] Added to Windows startup
echo.

REM Configure VS Code to show project folder in window title
echo [STEP 3/6] Configuring VS Code window title...
set "VSCODE_SETTINGS=%APPDATA%\Code\User\settings.json"
set "VSCODE_SETTINGS_DIR=%APPDATA%\Code\User"

if not exist "%VSCODE_SETTINGS_DIR%" mkdir "%VSCODE_SETTINGS_DIR%"

if exist "%VSCODE_SETTINGS%" (
    REM Check if window.title is already configured
    findstr /C:"window.title" "%VSCODE_SETTINGS%" >nul 2>&1
    if !errorlevel! neq 0 (
        REM Add window.title setting before the last closing brace
        powershell -Command "(Get-Content '%VSCODE_SETTINGS%' -Raw) -replace '\}$', ',  \"window.title\": \"${dirty}${activeEditorShort}${separator}${activeFolderShort}${separator}${appName}\"' + \"`n}\"" | Set-Content '%VSCODE_SETTINGS%'"
        echo [OK] VS Code configured to show project folder in title
    ) else (
        echo [OK] VS Code window.title already configured
    )
) else (
    REM Create new settings file
    echo { > "%VSCODE_SETTINGS%"
    echo   "window.title": "${dirty}${activeEditorShort}${separator}${activeFolderShort}${separator}${appName}" >> "%VSCODE_SETTINGS%"
    echo } >> "%VSCODE_SETTINGS%"
    echo [OK] VS Code settings created with project folder in title
)
echo.

REM Install VS Code ActivityWatch extension
echo [STEP 4/6] Installing VS Code ActivityWatch extension...
where code >nul 2>&1
if !errorlevel! equ 0 (
    code --install-extension activitywatch.aw-watcher-vscode --force >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] aw-watcher-vscode extension installed
    ) else (
        echo [WARN] Could not install extension. Install manually from VS Code Extensions.
    )
) else (
    echo [SKIP] VS Code not found in PATH. Install aw-watcher-vscode manually from Extensions.
)
echo.

REM Install Chrome ActivityWatch extension
echo [STEP 5/6] ActivityWatch Browser Extension...
echo.
echo   Opening Chrome Web Store - please click "Add to Chrome" to install.
echo.
start "" "https://chromewebstore.google.com/detail/activitywatch-web-watcher/nglaklhklhcoonedhgnpgddginnjdadi"
echo [OK] Chrome Web Store opened - click "Add to Chrome"
echo.
timeout /t 5 >nul

REM Start the service now
echo [STEP 6/6] Starting sync service...
start "" wscript.exe "%SCRIPT_DIR%\run_hidden.vbs"
echo [OK] Service started!
echo.

REM Show success
echo ============================================================
echo   INSTALLATION COMPLETE!
echo ============================================================
echo.
echo What happens now:
echo   - A green icon appears in your system tray (near clock)
echo   - Your activity syncs automatically every 5 minutes
echo   - Service starts automatically when Windows starts
echo.
echo Extensions installed:
echo   - aw-watcher-vscode: Tracks code project, file, language
echo   - aw-watcher-web:    Tracks browser URLs and domains
echo.
echo Your Developer ID: %USERNAME%
echo.
echo To check: Look for the green "AW" icon in your system tray
echo To stop:  Right-click the icon and select "Quit"
echo.
echo ============================================================
echo.
pause
