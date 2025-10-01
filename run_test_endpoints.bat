# run_test_endpoints.bat
@echo off
echo Testing ActivityWatch Sync Endpoints...
echo.

cd /d "E:\timesheet\timesheet_new"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate
) else (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    pip install requests
)

python test_endpoints.py

echo.
pause