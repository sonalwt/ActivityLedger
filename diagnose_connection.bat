@echo off
title Timesheet Connection Diagnostics
echo ========================================
echo Timesheet API Connection Diagnostics
echo ========================================
echo.
echo Running network diagnostics...
echo.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "network_diagnostic.ps1"
echo.
echo ========================================
echo Diagnostics complete!
echo.
echo If the DNS resolution failed, try:
echo 1. Check if you need to be on company VPN
echo 2. Contact IT for the correct server address
echo 3. Ask IT for the server IP address
echo ========================================
pause