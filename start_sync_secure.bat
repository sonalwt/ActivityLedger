@echo off
title ActivityWatch Sync - Secure Mode
echo ========================================
echo ActivityWatch Sync - Using Secure Credentials
echo ========================================
echo.
echo This uses credentials stored securely in Windows
echo If you haven't set up credentials, run manage_credentials.bat first
echo.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "sync_secure.ps1"
pause
