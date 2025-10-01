@echo off
echo.
echo Copying working sync files to Downloads...
echo.

copy /Y "E:\timesheet\timesheet_new\sync.ps1" "C:\Users\ankit\Downloads\sync.ps1"
copy /Y "E:\timesheet\timesheet_new\start_sync.bat" "C:\Users\ankit\Downloads\start_sync.bat"

echo.
echo ======================================
echo FILES COPIED SUCCESSFULLY!
echo ======================================
echo.
echo To start syncing:
echo 1. Go to your Downloads folder
echo 2. Double-click start_sync.bat
echo.
echo OR run in PowerShell:
echo cd Downloads
echo .\sync.ps1
echo.
echo NOTE: This version uses HTTP to avoid the 308 redirect issue.
echo.
pause