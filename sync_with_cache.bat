@echo off
REM sync_with_cache.bat - Sync with output caching

REM Set cache file location
set CACHE_FILE=%TEMP%\activitywatch_sync_cache.txt
set LOG_FILE=%TEMP%\activitywatch_sync_log.txt

REM Get current timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set timestamp=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%:%datetime:~12,2%

echo ========================================== >> %CACHE_FILE%
echo Sync started at %timestamp% >> %CACHE_FILE%
echo ========================================== >> %CACHE_FILE%

REM Run PowerShell sync script and cache output
powershell.exe -ExecutionPolicy Bypass -File sync.ps1 2>&1 | tee -a %CACHE_FILE%

REM Also save just the latest run to a separate file
powershell.exe -ExecutionPolicy Bypass -File sync.ps1 > %LOG_FILE% 2>&1

echo.
echo Output cached to: %CACHE_FILE%
echo Latest log: %LOG_FILE%
