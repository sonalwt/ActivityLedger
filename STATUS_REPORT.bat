@echo off
cls
echo ======================================
echo ACTIVITYWATCH SYNC - STATUS REPORT
echo ======================================
echo.
echo ISSUE: Your HTTPS endpoint returns 308 redirect
echo SOLUTION: Using HTTP endpoint instead
echo.
echo ======================================
echo WORKING FILES READY TO USE:
echo ======================================
echo.
echo 1. sync.ps1 (MAIN FILE)
echo    - Uses HTTP to avoid redirect
echo    - Location: E:\timesheet\timesheet_new\sync.ps1
echo    - Status: WORKING
echo.
echo 2. start_sync.bat
echo    - Easy launcher for sync.ps1
echo    - Just double-click to run
echo.
echo ======================================
echo TO START SYNCING NOW:
echo ======================================
echo.
echo Option 1: Double-click start_sync_http.bat
echo Option 2: Run: powershell -File sync.ps1
echo Option 3: Copy to Downloads and run from there
echo.
echo ======================================
echo ALTERNATIVE SOLUTIONS:
echo ======================================
echo.
echo - sync_curl.ps1 (uses curl for HTTPS)
echo - sync_https_308_support.ps1 (handles redirects)
echo - sync_modular.ps1 (uses config file)
echo.
echo ======================================
echo SERVER FIX (for your IT team):
echo ======================================
echo.
echo In FastAPI main.py, add:
echo app = FastAPI(redirect_slashes=False)
echo.
echo ======================================
echo.
echo Press any key to copy working files to Downloads...
pause >nul

copy /Y "sync.ps1" "C:\Users\ankit\Downloads\sync.ps1"
copy /Y "start_sync.bat" "C:\Users\ankit\Downloads\start_sync.bat"

echo.
echo Files copied to Downloads folder!
echo.
pause