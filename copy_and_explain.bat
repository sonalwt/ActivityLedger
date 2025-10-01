@echo off
echo.
echo Copying updated sync.ps1 to your Downloads folder...
echo.

copy /Y "E:\timesheet\timesheet_new\sync.ps1" "C:\Users\ankit\Downloads\sync.ps1"

echo.
echo ======================================
echo IMPORTANT: Server Configuration Issue
echo ======================================
echo.
echo Your server is returning 308 redirects for HTTPS requests.
echo The updated sync.ps1 uses HTTP to avoid this issue.
echo.
echo Options:
echo 1. Use the updated sync.ps1 (uses HTTP) - Recommended
echo 2. Try sync_curl.ps1 (uses curl for HTTPS)
echo 3. Try sync_autodetect.ps1 (tests all endpoints)
echo.
echo To fix the 308 redirect permanently, update your server's
echo FastAPI configuration with redirect_slashes=False
echo.
echo File copied to: C:\Users\ankit\Downloads\sync.ps1
echo.
pause