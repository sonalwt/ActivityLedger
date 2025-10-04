@echo off
title Developer Productivity Dashboard
echo ========================================
echo Starting Developer Productivity Dashboard
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created.
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt
echo.

REM Start the dashboard server
echo Starting dashboard server on http://localhost:5001
echo.
echo Press Ctrl+C to stop the server.
echo.
cd backend
python dashboard_api.py

pause
