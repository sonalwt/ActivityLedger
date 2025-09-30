@echo off
echo Copying clean sync.ps1 to Downloads folder...
echo.

REM Copy the clean version
copy /Y "E:\timesheet\timesheet_new\sync.ps1" "C:\Users\ankit\Downloads\sync.ps1"

echo.
echo File copied to: C:\Users\ankit\Downloads\sync.ps1
echo.
echo To run it:
echo 1. Open PowerShell
echo 2. Navigate to Downloads: cd Downloads
echo 3. Run: .\sync.ps1
echo.
echo Or run directly with:
echo powershell -ExecutionPolicy Bypass -File "C:\Users\ankit\Downloads\sync.ps1"
echo.
pause