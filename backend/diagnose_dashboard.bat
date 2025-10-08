@echo off
REM diagnose_dashboard.bat - Diagnose why dashboard shows 0 hours

echo === Dashboard Diagnosis ===
echo.

echo Running fixed duration check...
python debug_duration_issue_fixed.py

echo.
echo Press any key to check date issues...
pause > nul

echo.
echo Running date issue check...
python check_date_issue_fixed.py

echo.
echo === Diagnosis Complete ===
echo.
echo If your data is from an older date (not today):
echo 1. Look for the date picker in your dashboard
echo 2. Select the date shown above as "Latest"
echo 3. Your hours should appear immediately!
echo.
pause
