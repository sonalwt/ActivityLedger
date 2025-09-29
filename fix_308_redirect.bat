@echo off
REM fix_308_redirect.bat - Automatically fix 308 redirect issue

setlocal enabledelayedexpansion

cls
echo ========================================
echo ActivityWatch Sync 308 Redirect Fixer
echo ========================================
echo.

REM Check current sync.ps1
echo Checking current sync.ps1 configuration...
echo.

REM Find SERVER_URL in sync.ps1
powershell -Command "$content = Get-Content sync.ps1 -Raw; if ($content -match '\$SERVER_URL\s*=\s*\"(.*?)\"') { Write-Host 'Current SERVER_URL: ' $matches[1] -ForegroundColor Yellow }"

echo.
echo Testing server endpoints...
echo.

REM Test both HTTP and HTTPS
echo 1. Testing HTTPS (current):
powershell -Command "try { $r = Invoke-WebRequest 'https://api-timesheet.firsteconomy.com/api/sync' -Method POST -Body '{""test"":true}' -ContentType 'application/json' -MaximumRedirection 0 -ErrorAction SilentlyContinue; Write-Host '   Status:' $r.StatusCode -ForegroundColor Green } catch { if ($_.Exception.Response.StatusCode -eq 308) { Write-Host '   Status: 308 REDIRECT (This is the problem!)' -ForegroundColor Red } else { Write-Host '   Error:' $_.Exception.Message -ForegroundColor Red } }"

echo.
echo 2. Testing HTTP:
powershell -Command "try { $r = Invoke-WebRequest 'http://api-timesheet.firsteconomy.com/api/sync' -Method POST -Body '{""test"":true}' -ContentType 'application/json' -ErrorAction SilentlyContinue; Write-Host '   Status:' $r.StatusCode -ForegroundColor Green; Write-Host '   HTTP endpoint works!' -ForegroundColor Green } catch { Write-Host '   Error:' $_.Exception.Message -ForegroundColor Red }"

echo.
echo ========================================
echo.

REM Ask user to fix
choice /C YN /M "Do you want to fix the 308 redirect issue by changing to HTTP"
if %errorlevel%==1 (
    echo.
    echo Creating backup of sync.ps1...
    copy sync.ps1 sync.ps1.backup >nul 2>&1
    
    echo Updating sync.ps1 to use HTTP...
    powershell -Command "(Get-Content sync.ps1) -replace 'https://api-timesheet\.firsteconomy\.com', 'http://api-timesheet.firsteconomy.com' | Set-Content sync.ps1"
    
    echo.
    echo ✓ Fixed! Your sync.ps1 now uses HTTP.
    echo.
    echo Backup saved as: sync.ps1.backup
    echo.
    
    choice /C YN /M "Do you want to test the sync now"
    if !errorlevel!==1 (
        echo.
        echo Starting sync...
        powershell.exe -ExecutionPolicy Bypass -File sync.ps1
    )
) else (
    echo.
    echo Fix cancelled. You can manually edit sync.ps1 and change:
    echo   FROM: $SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
    echo   TO:   $SERVER_URL = "http://api-timesheet.firsteconomy.com/api/sync"
)

echo.
pause
