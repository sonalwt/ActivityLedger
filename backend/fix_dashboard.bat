@echo off
REM fix_dashboard.bat - Fix empty dashboard issue

echo === Fixing Empty Dashboard Issue ===
echo.

REM Run the diagnosis
echo Step 1: Running diagnosis...
echo.
python quick_dashboard_diagnosis.py

echo.
echo Press any key to apply the fix...
pause > nul

REM Apply the fix
echo.
echo Step 2: Applying the fix...
echo.
python flexible_dashboard_fix.py

echo.
echo === Fix Complete ===
echo.
echo Now restart your dashboard API by running:
echo    python dashboard_api_fixed.py
echo.
echo Then open http://localhost:5001 in your browser
echo.
pause
