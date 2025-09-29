@echo off
REM sync_with_report.bat - Sync with HTML report generation

setlocal enabledelayedexpansion

REM Configuration
set REPORT_DIR=%USERPROFILE%\Documents\ActivityWatchReports
set REPORT_FILE=%REPORT_DIR%\sync_report_%date:~-4,4%%date:~-10,2%%date:~-7,2%.html

REM Create report directory
if not exist "%REPORT_DIR%" mkdir "%REPORT_DIR%"

REM Start HTML report
echo ^<!DOCTYPE html^> > "%REPORT_FILE%"
echo ^<html^>^<head^> >> "%REPORT_FILE%"
echo ^<title^>ActivityWatch Sync Report - %date%^</title^> >> "%REPORT_FILE%"
echo ^<style^> >> "%REPORT_FILE%"
echo body { font-family: Arial, sans-serif; margin: 20px; } >> "%REPORT_FILE%"
echo .success { color: green; } >> "%REPORT_FILE%"
echo .error { color: red; } >> "%REPORT_FILE%"
echo .info { color: blue; } >> "%REPORT_FILE%"
echo table { border-collapse: collapse; width: 100%%; } >> "%REPORT_FILE%"
echo th, td { border: 1px solid #ddd; padding: 8px; text-align: left; } >> "%REPORT_FILE%"
echo th { background-color: #f2f2f2; } >> "%REPORT_FILE%"
echo ^</style^>^</head^>^<body^> >> "%REPORT_FILE%"
echo ^<h1^>ActivityWatch Sync Report^</h1^> >> "%REPORT_FILE%"
echo ^<p^>Generated: %date% %time%^</p^> >> "%REPORT_FILE%"
echo ^<h2^>Sync Log^</h2^> >> "%REPORT_FILE%"
echo ^<pre^> >> "%REPORT_FILE%"

REM Run sync and capture output
echo Running sync...
powershell.exe -ExecutionPolicy Bypass -Command "& {
    $output = & '.\sync.ps1' 2>&1
    $output | ForEach-Object {
        $line = $_
        if ($line -match 'successful|✓') {
            Write-Host $line -ForegroundColor Green
            '<span class=\"success\">' + $line + '</span>'
        } elseif ($line -match 'error|failed|❌') {
            Write-Host $line -ForegroundColor Red
            '<span class=\"error\">' + $line + '</span>'
        } else {
            Write-Host $line
            $line
        }
    }
}" >> "%REPORT_FILE%"

REM Close HTML
echo ^</pre^> >> "%REPORT_FILE%"
echo ^<p^>Report saved to: %REPORT_FILE%^</p^> >> "%REPORT_FILE%"
echo ^</body^>^</html^> >> "%REPORT_FILE%"

REM Open report in browser
start "" "%REPORT_FILE%"

echo.
echo Report saved to: %REPORT_FILE%
echo.
pause
