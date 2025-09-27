@echo off
echo ===================================
echo Timesheet Project Management Tools
echo ===================================
echo.
echo 1. Start Backend Server
echo 2. Start Frontend 
echo 3. Run Database Check
echo 4. Monitor Sync Status
echo 5. Test Sync Script
echo 6. View Logs
echo 7. Exit
echo.
set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto backend
if "%choice%"=="2" goto frontend
if "%choice%"=="3" goto dbcheck
if "%choice%"=="4" goto monitor
if "%choice%"=="5" goto testsync
if "%choice%"=="6" goto logs
if "%choice%"=="7" exit

:backend
cd backend
python run_backend.py
goto end

:frontend
cd frontend
npm start
goto end

:dbcheck
cd backend
python full_db_check.py
pause
goto end

:monitor
cd backend
python sync_monitor.py
goto end

:testsync
powershell -ExecutionPolicy Bypass -File sync.ps1
goto end

:logs
cd backend\logs
type *.log | more
pause
goto end

:end
pause
