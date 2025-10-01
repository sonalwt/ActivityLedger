@echo off
cls
color 0A
echo.
echo  ====================================================
echo   ACTIVITYWATCH SYNC - WORKING SOLUTION
echo  ====================================================
echo.
echo   Developer: ankita gholap
echo   Solution: Using HTTP to avoid 308 redirect
echo   Status: READY TO RUN
echo.
echo  ====================================================
echo.
echo  Starting sync in 3 seconds...
timeout /t 3 /nobreak >nul
echo.

cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -Command "& { Write-Host 'Sync started at:' (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') -ForegroundColor Cyan; & '.\sync.ps1' }"

echo.
echo  ====================================================
echo   If sync stopped, check:
echo   1. Is ActivityWatch running?
echo   2. Is your API token correct?
echo   3. Is the server accessible?
echo  ====================================================
echo.
pause