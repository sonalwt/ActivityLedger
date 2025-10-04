@echo off
title Timesheet Sync - Credential Manager
echo Running credential manager...
echo.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "manage_credentials.ps1"
pause
