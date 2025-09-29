@echo off
REM debug_sync.bat - Debug version with extensive logging

setlocal enabledelayedexpansion

REM Enable echo for debugging
echo on

REM Set log file
set DEBUG_LOG=sync_debug_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log
set DEBUG_LOG=%DEBUG_LOG: =0%

echo ===== DEBUG SYNC STARTED ===== > %DEBUG_LOG%
echo Date: %date% >> %DEBUG_LOG%
echo Time: %time% >> %DEBUG_LOG%
echo Current Directory: %cd% >> %DEBUG_LOG%
echo. >> %DEBUG_LOG%

REM Test server connectivity first
echo Testing server connectivity... >> %DEBUG_LOG%
echo. >> %DEBUG_LOG%

REM Test HTTP
echo Testing HTTP... >> %DEBUG_LOG%
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://api-timesheet.firsteconomy.com/api/sync' -Method HEAD -TimeoutSec 5; Write-Output 'HTTP Status: ' $response.StatusCode } catch { Write-Output 'HTTP Error: ' $_.Exception.Message }" >> %DEBUG_LOG% 2>&1

echo. >> %DEBUG_LOG%

REM Test HTTPS
echo Testing HTTPS... >> %DEBUG_LOG%
powershell -Command "try { $response = Invoke-WebRequest -Uri 'https://api-timesheet.firsteconomy.com/api/sync' -Method HEAD -TimeoutSec 5; Write-Output 'HTTPS Status: ' $response.StatusCode } catch { Write-Output 'HTTPS Error: ' $_.Exception.Message }" >> %DEBUG_LOG% 2>&1

echo. >> %DEBUG_LOG%

REM Check which PowerShell script exists
echo Checking for PowerShell scripts... >> %DEBUG_LOG%
if exist sync.ps1 (
    echo Found: sync.ps1 >> %DEBUG_LOG%
) else (
    echo NOT FOUND: sync.ps1 >> %DEBUG_LOG%
)

if exist sync_fixed.ps1 (
    echo Found: sync_fixed.ps1 >> %DEBUG_LOG%
) else (
    echo NOT FOUND: sync_fixed.ps1 >> %DEBUG_LOG%
)

echo. >> %DEBUG_LOG%

REM Show current sync.ps1 content (first few lines)
echo Current sync.ps1 SERVER_URL: >> %DEBUG_LOG%
powershell -Command "Get-Content sync.ps1 | Select-String 'SERVER_URL' | Select-Object -First 1" >> %DEBUG_LOG% 2>&1

echo. >> %DEBUG_LOG%

REM Run sync with detailed output
echo Running sync with debug output... >> %DEBUG_LOG%
echo. >> %DEBUG_LOG%

REM Run PowerShell with verbose output
powershell.exe -ExecutionPolicy Bypass -Command "
    Set-PSDebug -Trace 1
    $VerbosePreference = 'Continue'
    $DebugPreference = 'Continue'
    
    Write-Output '===== SYNC DEBUG START ====='
    Write-Output 'PowerShell Version: ' $PSVersionTable.PSVersion
    Write-Output 'Current Location: ' (Get-Location)
    
    # Check if using HTTPS or HTTP
    $content = Get-Content sync.ps1 -Raw
    if ($content -match 'https://') {
        Write-Output 'WARNING: Script is using HTTPS which causes 308 redirect!'
        Write-Output 'FIX: Change https:// to http:// in SERVER_URL'
    }
    
    # Try to run the sync
    try {
        & .\sync.ps1
    } catch {
        Write-Output 'ERROR: ' $_.Exception.Message
        Write-Output 'Stack Trace: ' $_.ScriptStackTrace
    }
" >> %DEBUG_LOG% 2>&1

echo. >> %DEBUG_LOG%
echo ===== DEBUG SYNC COMPLETED ===== >> %DEBUG_LOG%

REM Show results
echo.
echo Debug log saved to: %DEBUG_LOG%
echo.
type %DEBUG_LOG%
echo.
pause
