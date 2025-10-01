@echo off
cls
color 0C
echo.
echo  ====================================================
echo   CRITICAL: 308 REDIRECT ISSUE DETECTED
echo  ====================================================
echo.
echo  Your server is returning 308 redirects for ALL endpoints!
echo  This is preventing the sync script from working.
echo.
echo  ====================================================
echo   IMMEDIATE SOLUTIONS:
echo  ====================================================
echo.
echo  1. Run diagnostics   - Find where server redirects to
echo  2. Use curl version  - Better redirect handling  
echo  3. Use Python sync   - Most robust solution
echo  4. Contact IT team   - Fix server configuration
echo.
echo  ====================================================
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    echo.
    echo Running endpoint diagnostics...
    echo.
    powershell -ExecutionPolicy Bypass -File "diagnose_endpoints.ps1"
) else if "%choice%"=="2" (
    echo.
    echo Starting sync with curl (handles redirects better)...
    echo.
    powershell -ExecutionPolicy Bypass -File "sync_with_curl.ps1"
) else if "%choice%"=="3" (
    echo.
    echo Starting Python sync...
    echo.
    if exist venv\Scripts\activate.bat (
        call venv\Scripts\activate
    ) else (
        echo Installing Python requirements...
        python -m venv venv
        call venv\Scripts\activate
        pip install requests
    )
    python sync_python.py
) else if "%choice%"=="4" (
    echo.
    echo  ====================================================
    echo   SERVER CONFIGURATION FIX NEEDED:
    echo  ====================================================
    echo.
    echo  The server at api-timesheet.firsteconomy.com is
    echo  configured to redirect ALL requests with 308.
    echo.
    echo  Tell your IT team to:
    echo  1. Check nginx/Apache redirect rules
    echo  2. In FastAPI: app = FastAPI(redirect_slashes=False^)
    echo  3. Ensure /api/sync accepts POST without redirect
    echo.
    echo  Current behavior:
    echo  - http://api-timesheet.firsteconomy.com/api/sync → 308
    echo  - https://api-timesheet.firsteconomy.com/api/sync → 308
    echo.
    echo  ====================================================
    echo.
    pause
) else (
    echo.
    echo Invalid choice. Please run again.
    echo.
    timeout /t 3
)

echo.
pause