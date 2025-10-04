@echo off
title ActivityWatch Sync - Enhanced with Server Testing
echo ========================================
echo ActivityWatch Sync - Enhanced Version
echo ========================================
echo.
echo This version includes:
echo - Dynamic credential configuration
echo - Automatic server connection testing
echo - Better error handling
echo.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "sync_enhanced_dynamic.ps1"
pause
