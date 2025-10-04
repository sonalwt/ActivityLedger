@echo off
title Dashboard Quick Setup
echo ========================================
echo DEVELOPER PRODUCTIVITY DASHBOARD SETUP
echo ========================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please edit the .env file with your database credentials!
    echo Opening .env file...
    notepad .env
    pause
)

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt
echo.

REM Test database connection
echo Testing database connection...
cd backend
python -c "from dashboard_api_enhanced import analyzer; conn = analyzer.get_connection(); print('Database connection successful!'); conn.close()" 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Could not connect to database!
    echo Please check your .env file and ensure PostgreSQL is running.
    pause
    exit /b 1
)

echo.
echo ========================================
echo SETUP COMPLETE!
echo ========================================
echo.
echo To start the dashboard:
echo   Run: start_dashboard.bat
echo   Open: http://localhost:5001
echo.
echo To fix DNS issues for sync:
echo   Run: diagnose_connection.bat
echo.
pause
