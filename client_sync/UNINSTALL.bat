@echo off
REM ============================================================
REM ActivityWatch Auto-Sync - Uninstaller
REM ============================================================

echo.
echo ============================================================
echo   ActivityWatch Auto-Sync Uninstaller
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

REM Kill running process
echo Stopping sync service...
taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq ActivityWatch*" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq ActivityWatch*" >nul 2>&1

REM Remove from startup folder
echo Removing from startup...
del "%STARTUP%\ActivityWatch-AutoSync.vbs" >nul 2>&1
del "%STARTUP%\ActivityWatch-Sync.vbs" >nul 2>&1

REM Remove registry entry
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ActivityWatchAutoSync" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ActivityWatchSync" /f >nul 2>&1

REM Remove lock and marker files
del "%SCRIPT_DIR%\.sync_lock" >nul 2>&1
del "%SCRIPT_DIR%\.installed" >nul 2>&1

echo.
echo ============================================================
echo   UNINSTALL COMPLETE!
echo ============================================================
echo.
echo The sync service has been stopped and removed from startup.
echo.
pause
