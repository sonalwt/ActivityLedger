@echo off
REM ============================================================
REM ActivityWatch Sync - Auto-Start Installer
REM This script installs the sync client to run automatically
REM on Windows startup with system tray notification
REM ============================================================

setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo   ActivityWatch Sync - Auto-Start Installer
echo ============================================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Check for admin rights (needed for scheduled tasks)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Running without admin rights.
    echo           Some features may not work. Consider running as Administrator.
    echo.
)

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is required but not installed.
    echo         Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist "%SCRIPT_DIR%\.env" (
    if exist "%SCRIPT_DIR%\.env.template" (
        copy "%SCRIPT_DIR%\.env.template" "%SCRIPT_DIR%\.env" >nul
        echo [WARNING] Created .env file from template.
        echo           Please edit .env with your credentials before continuing.
        echo.
        notepad "%SCRIPT_DIR%\.env"
        pause
    ) else (
        echo [ERROR] No .env file found. Please create one with your credentials.
        pause
        exit /b 1
    )
)

REM Check if virtual environment exists
if not exist "%SCRIPT_DIR%\venv\Scripts\python.exe" (
    echo [INFO] Setting up virtual environment...
    python -m venv "%SCRIPT_DIR%\venv"
    call "%SCRIPT_DIR%\venv\Scripts\activate.bat"
    pip install -r "%SCRIPT_DIR%\requirements.txt" -q
    pip install pystray pillow -q
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment found.
    REM Ensure pystray is installed for system tray
    call "%SCRIPT_DIR%\venv\Scripts\activate.bat"
    pip install pystray pillow -q 2>nul
)

echo.
echo [STEP 1] Creating launcher scripts...

REM Create the hidden launcher VBS script
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%SCRIPT_DIR%"
echo WshShell.Run "cmd /c ""%SCRIPT_DIR%\run_sync.bat""", 0, False
) > "%SCRIPT_DIR%\hidden_launcher.vbs"
echo [OK] Created hidden_launcher.vbs

REM Create the main run script
(
echo @echo off
echo cd /d "%SCRIPT_DIR%"
echo call venv\Scripts\activate.bat
echo python sync_with_tray.py
) > "%SCRIPT_DIR%\run_sync.bat"
echo [OK] Created run_sync.bat

REM Create visible launcher for manual start
(
echo @echo off
echo cd /d "%SCRIPT_DIR%"
echo call venv\Scripts\activate.bat
echo echo ============================================================
echo echo   ActivityWatch Sync Client
echo echo   Press Ctrl+C to stop
echo echo ============================================================
echo echo.
echo python activitywatch_sync.py --continuous
echo pause
) > "%SCRIPT_DIR%\start_visible.bat"
echo [OK] Created start_visible.bat

echo.
echo [STEP 2] Installing auto-start methods...

REM Method 1: Startup folder shortcut
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\ActivityWatch-Sync.vbs"

REM Create startup VBS that shows notification
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%SCRIPT_DIR%"
echo ' Show balloon notification
echo Set objShell = CreateObject^("Shell.Application"^)
echo WshShell.Run "cmd /c ""%SCRIPT_DIR%\run_sync.bat""", 0, False
) > "%SHORTCUT_PATH%"
echo [OK] Added to Startup folder

REM Method 2: Registry auto-start (backup method)
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ActivityWatchSync" /t REG_SZ /d "wscript.exe \"%SCRIPT_DIR%\hidden_launcher.vbs\"" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Added to Registry startup
) else (
    echo [WARNING] Could not add Registry entry
)

REM Method 3: Scheduled Task (most reliable)
schtasks /delete /tn "ActivityWatchSync-Logon" /f >nul 2>&1
schtasks /create /tn "ActivityWatchSync-Logon" /tr "wscript.exe \"%SCRIPT_DIR%\hidden_launcher.vbs\"" /sc onlogon /rl limited /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Created scheduled task (on logon)
) else (
    echo [WARNING] Could not create scheduled task
)

echo.
echo [STEP 3] Testing ActivityWatch connection...
curl -s http://localhost:5600/api/0/buckets/ >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ActivityWatch is running
) else (
    echo [WARNING] ActivityWatch is not running. Please start it.
)

echo.
echo ============================================================
echo   INSTALLATION COMPLETE!
echo ============================================================
echo.
echo The sync client will now:
echo   - Start automatically when you log in
echo   - Show a system tray icon (look for it near the clock)
echo   - Sync your ActivityWatch data every 5 minutes
echo.
echo To start manually:    run_sync.bat (hidden) or start_visible.bat
echo To check status:      check_status.bat
echo To uninstall:         uninstall_autostart.bat
echo.
echo Would you like to start the sync client now? (Y/N)
set /p START_NOW="> "
if /i "%START_NOW%"=="Y" (
    echo.
    echo Starting sync client with system tray icon...
    start "" wscript.exe "%SCRIPT_DIR%\hidden_launcher.vbs"
    echo [OK] Sync client started! Look for the icon in your system tray.
)

echo.
pause
