@echo off
REM quick_fix.bat - One-click fix for 308 redirect

cls
echo Fixing 308 PERMANENT REDIRECT error...
echo.

REM Create backup
copy sync.ps1 sync.ps1.backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.bak >nul 2>&1

REM Fix the URL
powershell -Command "(Get-Content sync.ps1) -replace 'https://api-timesheet\.firsteconomy\.com', 'http://api-timesheet.firsteconomy.com' | Set-Content sync.ps1"

echo ✓ Fixed! Changed HTTPS to HTTP in sync.ps1
echo.
echo Backup saved with timestamp
echo.
echo Starting sync with fixed configuration...
echo.

powershell.exe -ExecutionPolicy Bypass -File sync.ps1
