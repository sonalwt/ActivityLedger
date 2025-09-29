@echo off
REM setup_scheduled_sync.bat - Set up scheduled task with caching

echo Setting up scheduled ActivityWatch sync with caching...

REM Create cache directory
set CACHE_DIR=%LOCALAPPDATA%\ActivityWatchSync
if not exist "%CACHE_DIR%" mkdir "%CACHE_DIR%"

REM Create the sync wrapper script
echo @echo off > "%CACHE_DIR%\scheduled_sync.bat"
echo cd /d "E:\timesheet\timesheet_new" >> "%CACHE_DIR%\scheduled_sync.bat"
echo echo %%date%% %%time%% - Starting sync... ^>^> "%%CACHE_DIR%%\sync_history.log" >> "%CACHE_DIR%\scheduled_sync.bat"
echo powershell.exe -ExecutionPolicy Bypass -File sync.ps1 ^>^> "%%CACHE_DIR%%\last_sync.log" 2^>^&1 >> "%CACHE_DIR%\scheduled_sync.bat"
echo echo %%date%% %%time%% - Sync completed ^>^> "%%CACHE_DIR%%\sync_history.log" >> "%CACHE_DIR%\scheduled_sync.bat"

REM Create scheduled task (runs every 5 minutes)
schtasks /create /tn "ActivityWatchSync" /tr "%CACHE_DIR%\scheduled_sync.bat" /sc minute /mo 5 /f

REM Create a viewer script
echo @echo off > view_sync_logs.bat
echo echo === Last Sync Results === >> view_sync_logs.bat
echo type "%CACHE_DIR%\last_sync.log" >> view_sync_logs.bat
echo echo. >> view_sync_logs.bat
echo echo === Sync History === >> view_sync_logs.bat
echo type "%CACHE_DIR%\sync_history.log" ^| more >> view_sync_logs.bat
echo pause >> view_sync_logs.bat

echo.
echo Scheduled task created!
echo - Syncs every 5 minutes
echo - Logs saved to: %CACHE_DIR%
echo - View logs: run view_sync_logs.bat
echo.
pause
