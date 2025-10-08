@echo off
REM diagnose_500_error.bat - Diagnose the API 500 error

echo =====================================
echo   DIAGNOSING API 500 ERROR
echo =====================================
echo.

echo Step 1: Running API error diagnosis...
python debug_api_error.py

echo.
echo Press any key to continue...
pause > nul

echo.
echo Step 2: Running fixes for common issues...
python fix_activity_api_500.py

echo.
echo =====================================
echo   MOST LIKELY CAUSES:
echo =====================================
echo.
echo 1. CASE SENSITIVITY: 
echo    - URL shows "riddhidhakhara" (lowercase)
echo    - Database might have "RiddhiDhakhara" (capitalized)
echo.
echo 2. DATE RANGE ISSUE:
echo    - Querying Sep 30 - Oct 8, 2025
echo    - Your data might be from Oct 1-2, 2025 only
echo.
echo 3. NULL VALUES:
echo    - Missing application_name or category
echo    - Can cause API queries to fail
echo.
echo =====================================
echo   IMMEDIATE FIXES:
echo =====================================
echo.
echo 1. Check the server logs for the exact error
echo 2. Update API to use case-insensitive queries
echo 3. Add error handling to return proper messages
echo.
pause
