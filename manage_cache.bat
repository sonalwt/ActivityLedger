@echo off
REM manage_cache.bat - Manage ActivityWatch sync cache

:menu
cls
echo ========================================
echo ActivityWatch Sync Cache Manager
echo ========================================
echo.
echo 1. View cache statistics
echo 2. Clear event cache
echo 3. Clear all logs
echo 4. Backup cache
echo 5. Restore cache
echo 6. Exit
echo.
set /p choice=Enter your choice (1-6): 

if "%choice%"=="1" goto view_stats
if "%choice%"=="2" goto clear_cache
if "%choice%"=="3" goto clear_logs
if "%choice%"=="4" goto backup_cache
if "%choice%"=="5" goto restore_cache
if "%choice%"=="6" exit
goto menu

:view_stats
cls
echo === Cache Statistics ===
echo.
set CACHE_DIR=%TEMP%\ActivityWatchCache
if exist "%CACHE_DIR%\synced_events.json" (
    echo Event Cache:
    for %%A in ("%CACHE_DIR%\synced_events.json") do echo   Size: %%~zA bytes
    powershell -Command "& {
        $cache = Get-Content '%CACHE_DIR%\synced_events.json' | ConvertFrom-Json
        Write-Host '  Events cached:' $cache.syncedEventIds.Count
        Write-Host '  Last sync:' $cache.lastSync
    }"
) else (
    echo   No event cache found
)
echo.
if exist "%CACHE_DIR%\sync_log.txt" (
    echo Log File:
    for %%A in ("%CACHE_DIR%\sync_log.txt") do echo   Size: %%~zA bytes
    for /f %%C in ('find /c /v "" ^<"%CACHE_DIR%\sync_log.txt"') do echo   Lines: %%C
)
echo.
pause
goto menu

:clear_cache
cls
echo Clearing event cache...
if exist "%TEMP%\ActivityWatchCache\synced_events.json" (
    del "%TEMP%\ActivityWatchCache\synced_events.json"
    echo Event cache cleared!
) else (
    echo No event cache found
)
pause
goto menu

:clear_logs
cls
echo Clearing all logs...
if exist "%TEMP%\ActivityWatchCache\*.log" del "%TEMP%\ActivityWatchCache\*.log"
if exist "%TEMP%\ActivityWatchCache\*.txt" del "%TEMP%\ActivityWatchCache\*.txt"
if exist "%TEMP%\activitywatch_sync_cache.txt" del "%TEMP%\activitywatch_sync_cache.txt"
echo Logs cleared!
pause
goto menu

:backup_cache
cls
echo Backing up cache...
set BACKUP_DIR=%USERPROFILE%\Documents\ActivityWatchBackup
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
set BACKUP_FILE=%BACKUP_DIR%\cache_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%.zip
powershell -Command "Compress-Archive -Path '%TEMP%\ActivityWatchCache\*' -DestinationPath '%BACKUP_FILE%' -Force"
echo Cache backed up to: %BACKUP_FILE%
pause
goto menu

:restore_cache
cls
echo Available backups:
dir "%USERPROFILE%\Documents\ActivityWatchBackup\*.zip" /b 2>NUL
echo.
set /p backup_file=Enter backup filename to restore (or 'cancel'): 
if "%backup_file%"=="cancel" goto menu
if exist "%USERPROFILE%\Documents\ActivityWatchBackup\%backup_file%" (
    powershell -Command "Expand-Archive -Path '%USERPROFILE%\Documents\ActivityWatchBackup\%backup_file%' -DestinationPath '%TEMP%\ActivityWatchCache' -Force"
    echo Cache restored!
) else (
    echo Backup file not found!
)
pause
goto menu
