@echo off
REM complete_dashboard_fix.bat - Complete fix for dashboard issues

echo === Complete Dashboard Fix ===
echo.

echo Step 1: Debugging the issue...
echo ==============================
python debug_duration_issue.py

echo.
echo Press any key to continue...
pause > nul

echo.
echo Step 2: Checking date issues...
echo ===============================
python check_date_issue.py

echo.
echo Press any key to continue...
pause > nul

echo.
echo Step 3: Fixing duration data...
echo ===============================
python fix_duration_data.py

echo.
echo Step 4: Extracting app data from JSON...
echo ========================================
python flexible_dashboard_fix.py

echo.
echo === Fix Complete ===
echo.
echo Now restart your dashboard API and check again.
echo If the dashboard still shows 0h, try selecting a different date.
echo.
pause
