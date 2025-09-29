@echo off
REM apply_https_fix.bat - Apply the HTTPS fix

cls
echo ========================================
echo Applying HTTPS Fix to sync.ps1
echo ========================================
echo.

echo Current configuration:
powershell -Command "(Get-Content sync.ps1 | Select-String 'SERVER_URL').Line"
echo.

echo Fixing to use: https://api-timesheet.firsteconomy.com/api/sync
echo.

REM Backup current sync.ps1
copy sync.ps1 sync.ps1.backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.bak >nul 2>&1

REM Update to correct HTTPS URL without trailing slash
powershell -Command "(Get-Content sync.ps1) -replace '\$SERVER_URL = .*', '$SERVER_URL = \"https://api-timesheet.firsteconomy.com/api/sync\"' | Set-Content sync.ps1"

echo ✓ Fixed! Updated to use HTTPS without trailing slash
echo.
echo New configuration:
powershell -Command "(Get-Content sync.ps1 | Select-String 'SERVER_URL').Line"
echo.
echo Starting sync with fixed URL...
echo.

powershell.exe -ExecutionPolicy Bypass -File sync.ps1
