@echo off
title ActivityWatch Sync - ankita gholap
echo Starting ActivityWatch sync...
echo Using HTTP endpoint (avoids 308 redirect issue)
echo.
cd /d "E:\timesheet\timesheet_new"
powershell -ExecutionPolicy Bypass -File "sync.ps1"
pause