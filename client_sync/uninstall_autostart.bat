@echo off
REM ============================================================
REM ActivityWatch Sync - Uninstall Auto-Start
REM ============================================================

echo.
echo ============================================================
echo   ActivityWatch Sync - Uninstall Auto-Start
echo ============================================================
echo.
echo This will remove all auto-start configurations.
echo The sync client files will NOT be deleted.
echo.
set /p CONFIRM="Are you sure? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo Removing auto-start configurations...

REM Stop running processes
echo [1/4] Stopping running sync processes...
taskkill /f /fi "WINDOWTITLE eq ActivityWatch*" >nul 2>&1
wmic process where "commandline like '%%sync_with_tray%%'" delete >nul 2>&1
wmic process where "commandline like '%%activitywatch_sync%%'" delete >nul 2>&1

REM Remove Startup folder entry
echo [2/4] Removing Startup folder entry...
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ActivityWatch-Sync.vbs" >nul 2>&1
if %errorlevel% equ 0 (
    echo       Removed startup folder entry
) else (
    echo       No startup folder entry found
)

REM Remove Registry entry
echo [3/4] Removing Registry entry...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ActivityWatchSync" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo       Removed registry entry
) else (
    echo       No registry entry found
)

REM Remove Scheduled Task
echo [4/4] Removing Scheduled Task...
schtasks /delete /tn "ActivityWatchSync-Logon" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo       Removed scheduled task
) else (
    echo       No scheduled task found
)

echo.
echo ============================================================
echo   Uninstall complete!
echo ============================================================
echo.
echo Auto-start has been disabled.
echo To re-enable, run: install_autostart.bat
echo.
pause
