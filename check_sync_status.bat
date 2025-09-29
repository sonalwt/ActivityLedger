@echo off
REM check_sync_status.bat - Quick check of sync status from cache

setlocal enabledelayedexpansion

REM Cache locations
set CACHE_FILE=%TEMP%\ActivityWatchCache\synced_events.json
set LOG_FILE=%TEMP%\ActivityWatchCache\sync_log.txt
set LAST_OUTPUT=%TEMP%\activitywatch_sync_cache.txt

echo ========================================
echo ActivityWatch Sync Status Check
echo ========================================
echo.

REM Check if sync is currently running
tasklist /FI "WINDOWTITLE eq ActivityWatch Sync*" 2>NUL | find /I "powershell.exe" >NUL
if %errorlevel% == 0 (
    echo Status: [RUNNING] Sync is currently active
) else (
    echo Status: [STOPPED] Sync is not running
)
echo.

REM Check last sync time from cache
if exist "%CACHE_FILE%" (
    echo === Last Sync Info ===
    powershell -Command "& {
        $cache = Get-Content '%CACHE_FILE%' | ConvertFrom-Json
        Write-Host 'Last sync time:' $cache.lastSync
        Write-Host 'Events synced:' $cache.syncedEventIds.Count
    }"
) else (
    echo No sync cache found
)
echo.

REM Show recent log entries
if exist "%LOG_FILE%" (
    echo === Recent Activity ===
    powershell -Command "Get-Content '%LOG_FILE%' -Tail 10"
) else (
    echo No log file found
)
echo.

REM Show last sync output summary
if exist "%LAST_OUTPUT%" (
    echo === Last Sync Summary ===
    powershell -Command "& {
        $content = Get-Content '%LAST_OUTPUT%' -Tail 20
        $content | Where-Object { $_ -match 'successful|error|failed|Sending|Found' }
    }"
)

echo.
echo ========================================
echo Cache locations:
echo - Events: %CACHE_FILE%
echo - Logs: %LOG_FILE%
echo - Output: %LAST_OUTPUT%
echo ========================================
echo.
pause
