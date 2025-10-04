@echo off
title ActivityWatch Sync - Fixed Version
echo Starting ActivityWatch sync (Fixed Version)...
echo This version includes better error handling and connection testing
echo.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "sync_fixed.ps1"
pause