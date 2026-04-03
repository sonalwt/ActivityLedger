@echo off
REM ============================================================
REM ActivityWatch Auto-Sync - Universal Installer
REM Works on ANY Windows PC - No Python needed!
REM ============================================================

setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo   ActivityWatch Auto-Sync - Universal Installer
echo   No Python required - Works on any Windows PC!
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Check if Python exists
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python found - using Python installer
    call "%SCRIPT_DIR%\INSTALL.bat"
    exit /b 0
)

echo [INFO] Python not found - using PowerShell method
echo.

REM Check PowerShell (available on all Windows 7+)
powershell -Command "echo test" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PowerShell not available. Please install Python.
    pause
    exit /b 1
)

echo [STEP 1/3] Setting up sync service...

REM Create the PowerShell sync script
powershell -ExecutionPolicy Bypass -Command ^
    "$script = @'" & echo. & ^
    "Add-Content"

REM Create PowerShell script file
call :CreatePowerShellScript

echo [OK] Sync script created
echo.

echo [STEP 2/3] Installing to Windows startup...

REM Add to startup folder
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
copy /Y "%SCRIPT_DIR%\run_sync.vbs" "%STARTUP%\ActivityWatch-Sync.vbs" >nul 2>&1

echo [OK] Added to startup
echo.

echo [STEP 3/3] Starting sync service...
start "" wscript.exe "%SCRIPT_DIR%\run_sync.vbs"

echo.
echo ============================================================
echo   INSTALLATION COMPLETE!
echo ============================================================
echo.
echo Your activity will now sync automatically.
echo Look for a notification icon in your system tray.
echo.
pause
exit /b 0

:CreatePowerShellScript
REM Create the main PowerShell sync script
(
echo # ActivityWatch Auto-Sync Service ^(PowerShell^)
echo # No Python required - runs on any Windows PC
echo.
echo $ServerUrl = "https://api-timesheet.firsteconomy.com/api/sync"
echo $ActivityWatchHost = "http://localhost:5600"
echo $SyncIntervalMinutes = 5
echo.
echo # Auto-detect developer identity
echo $DeveloperId = $env:USERNAME.ToLower^(^) -replace ' ', '-'
echo $Hostname = $env:COMPUTERNAME
echo $MachineId = [System.BitConverter]::ToString^([System.Security.Cryptography.MD5]::Create^(^).ComputeHash^([System.Text.Encoding]::UTF8.GetBytes^("$Hostname-$env:USERNAME"^)^)^).Replace^("-", ""^).Substring^(0, 12^).ToLower^(^)
echo $ApiToken = "auto-$MachineId"
echo.
echo $LogFile = Join-Path $PSScriptRoot "sync.log"
echo.
echo function Write-Log^($msg^) {
echo     $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
echo     "$timestamp - $msg" ^| Out-File -Append $LogFile
echo }
echo.
echo function Get-ActivityData^($hoursBack^) {
echo     try {
echo         $endTime = [DateTime]::UtcNow
echo         $startTime = $endTime.AddHours^(-$hoursBack^)
echo.
echo         $bucketsUrl = "$ActivityWatchHost/api/0/buckets/"
echo         $buckets = Invoke-RestMethod -Uri $bucketsUrl -TimeoutSec 10
echo.
echo         $activities = @^(^)
echo.
echo         foreach ^($bucketName in $buckets.PSObject.Properties.Name^) {
echo             if ^($bucketName -match "afk"^) { continue }
echo.
echo             $eventsUrl = "$ActivityWatchHost/api/0/buckets/$bucketName/events"
echo             $params = @{
echo                 start = $startTime.ToString^("yyyy-MM-ddTHH:mm:ss"^)
echo                 end = $endTime.ToString^("yyyy-MM-ddTHH:mm:ss"^)
echo                 limit = 5000
echo             }
echo.
echo             try {
echo                 $events = Invoke-RestMethod -Uri $eventsUrl -Body $params -TimeoutSec 15
echo.
echo                 foreach ^($event in $events^) {
echo                     if ^($event.duration -lt 5^) { continue }
echo.
echo                     $app = $event.data.app
echo                     if ^(-not $app^) { $app = $event.data.application }
echo                     if ^(-not $app^) { continue }
echo.
echo                     $activities += @{
echo                         timestamp = $event.timestamp
echo                         duration = $event.duration
echo                         data = @{
echo                             app = $app
echo                             title = $event.data.title
echo                             url = $event.data.url
echo                         }
echo                     }
echo                 }
echo             } catch {
echo                 Write-Log "Error fetching $bucketName : $_"
echo             }
echo         }
echo.
echo         return $activities
echo     } catch {
echo         Write-Log "Error connecting to ActivityWatch: $_"
echo         return @^(^)
echo     }
echo }
echo.
echo function Send-ToServer^($activities^) {
echo     if ^($activities.Count -eq 0^) {
echo         Write-Log "No activities to sync"
echo         return $true
echo     }
echo.
echo     $payload = @{
echo         name = $DeveloperId
echo         token = $ApiToken
echo         hostname = $Hostname
echo         data = $activities
echo         timestamp = [DateTime]::UtcNow.ToString^("o"^)
echo     } ^| ConvertTo-Json -Depth 10
echo.
echo     try {
echo         $response = Invoke-RestMethod -Uri $ServerUrl -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 30
echo.
echo         if ^($response.success^) {
echo             Write-Log "Synced $^($activities.Count^) activities"
echo             return $true
echo         } else {
echo             Write-Log "Server error: $^($response.error^)"
echo             return $false
echo         }
echo     } catch {
echo         Write-Log "Sync failed: $_"
echo         return $false
echo     }
echo }
echo.
echo function Show-Notification^($title, $message^) {
echo     try {
echo         [System.Reflection.Assembly]::LoadWithPartialName^("System.Windows.Forms"^) ^| Out-Null
echo         $notify = New-Object System.Windows.Forms.NotifyIcon
echo         $notify.Icon = [System.Drawing.SystemIcons]::Information
echo         $notify.BalloonTipTitle = $title
echo         $notify.BalloonTipText = $message
echo         $notify.Visible = $true
echo         $notify.ShowBalloonTip^(5000^)
echo         Start-Sleep -Seconds 5
echo         $notify.Dispose^(^)
echo     } catch {}
echo }
echo.
echo # Main
echo Write-Log "=========================================="
echo Write-Log "ActivityWatch Sync Starting"
echo Write-Log "Developer: $DeveloperId"
echo Write-Log "=========================================="
echo.
echo Show-Notification "ActivityWatch Sync" "Sync started for $DeveloperId"
echo.
echo # Initial sync - last 24 hours
echo Write-Log "Initial sync ^(last 24 hours^)..."
echo $activities = Get-ActivityData 24
echo Send-ToServer $activities
echo.
echo # Continuous sync loop
echo while ^($true^) {
echo     Start-Sleep -Seconds ^($SyncIntervalMinutes * 60^)
echo.
echo     Write-Log "Running scheduled sync..."
echo     $activities = Get-ActivityData ^($SyncIntervalMinutes / 60 + 0.5^)
echo     Send-ToServer $activities
echo }
) > "%SCRIPT_DIR%\sync_service.ps1"

REM Create VBS launcher to run hidden
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%SCRIPT_DIR%"
echo WshShell.Run "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File ""%SCRIPT_DIR%\sync_service.ps1""", 0, False
) > "%SCRIPT_DIR%\run_sync.vbs"

goto :eof
