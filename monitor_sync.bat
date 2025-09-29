@echo off
REM monitor_sync.bat - Real-time monitoring of sync process

cls
echo ========================================
echo ActivityWatch Sync Monitor
echo ========================================
echo.
echo This will show detailed information about each sync attempt
echo Press Ctrl+C to stop
echo.
echo Starting monitor...
echo.

REM Create monitoring PowerShell script
powershell.exe -ExecutionPolicy Bypass -Command "
$host.UI.RawUI.WindowTitle = 'ActivityWatch Sync Monitor'

# Colors
function Write-ColorHost($Text, $Color = 'White') {
    Write-Host $Text -ForegroundColor $Color -NoNewline
}

# Monitor function
function Monitor-Sync {
    $DEVELOPER_NAME = 'ankita gholap'
    $API_TOKEN = 'AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs'
    $SERVER_URL = if ((Get-Content sync.ps1 -Raw) -match '\$SERVER_URL\s*=\s*\"([^\"]+)\"') { $matches[1] } else { 'Unknown' }
    $LOCAL_AW = 'http://localhost:5600/api/0'
    
    Write-Host ''
    Write-Host 'Current Configuration:' -ForegroundColor Cyan
    Write-Host '  Developer: ' -NoNewline; Write-Host $DEVELOPER_NAME -ForegroundColor Yellow
    Write-Host '  Server URL: ' -NoNewline; 
    if ($SERVER_URL -like 'https://*') {
        Write-Host $SERVER_URL -ForegroundColor Red
        Write-Host '  ⚠️  WARNING: Using HTTPS will cause 308 redirect!' -ForegroundColor Red
    } else {
        Write-Host $SERVER_URL -ForegroundColor Green
    }
    Write-Host ''
    
    $syncCount = 0
    $errorCount = 0
    
    while ($true) {
        $syncCount++
        $timestamp = Get-Date -Format 'HH:mm:ss'
        
        Write-Host '─────────────────────────────────────────' -ForegroundColor DarkGray
        Write-Host "[$timestamp] Sync attempt #$syncCount" -ForegroundColor White
        
        # Check ActivityWatch
        Write-Host '  • Checking ActivityWatch... ' -NoNewline
        try {
            $awInfo = Invoke-RestMethod -Uri '$LOCAL_AW/info' -Method GET -TimeoutSec 2
            Write-Host 'Connected' -ForegroundColor Green
        } catch {
            Write-Host 'Not running!' -ForegroundColor Red
            Write-Host '    Fix: Start ActivityWatch' -ForegroundColor Yellow
            $errorCount++
        }
        
        # Get events
        Write-Host '  • Getting events... ' -NoNewline
        try {
            $buckets = (Invoke-RestMethod -Uri '$LOCAL_AW/buckets' -Method GET -TimeoutSec 5).PSObject.Properties.Name
            $totalEvents = 0
            
            $endTime = (Get-Date).ToUniversalTime()
            $startTime = $endTime.AddMinutes(-6)
            
            foreach ($bucket in $buckets) {
                $eventsUrl = \"$LOCAL_AW/buckets/$bucket/events?start=$($startTime.ToString('yyyy-MM-ddTHH:mm:ss.fffZ'))&end=$($endTime.ToString('yyyy-MM-ddTHH:mm:ss.fffZ'))\"
                $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 5
                $totalEvents += $events.Count
            }
            
            Write-Host \"$totalEvents events from $($buckets.Count) buckets\" -ForegroundColor Green
            
            if ($totalEvents -gt 0) {
                # Test sync
                Write-Host '  • Sending to server... ' -NoNewline
                
                $payload = @{
                    name = $DEVELOPER_NAME
                    token = $API_TOKEN
                    data = @(@{timestamp='test'; duration=1; data=@{}})
                    timestamp = $endTime.ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
                } | ConvertTo-Json -Depth 10
                
                try {
                    $response = Invoke-WebRequest -Uri $SERVER_URL `
                        -Method POST `
                        -Body $payload `
                        -ContentType 'application/json' `
                        -TimeoutSec 10 `
                        -MaximumRedirection 0
                    
                    Write-Host 'Success!' -ForegroundColor Green
                } catch {
                    if ($_.Exception.Response.StatusCode -eq 308) {
                        Write-Host '308 REDIRECT!' -ForegroundColor Red
                        Write-Host '    Fix: Change https:// to http:// in sync.ps1' -ForegroundColor Yellow
                        $errorCount++
                    } else {
                        Write-Host \"Error: $($_.Exception.Message)\" -ForegroundColor Red
                        $errorCount++
                    }
                }
            } else {
                Write-Host '  • No new events to sync' -ForegroundColor Gray
            }
            
        } catch {
            Write-Host 'Failed!' -ForegroundColor Red
            $errorCount++
        }
        
        # Stats
        Write-Host ''
        Write-Host \"  Stats: $syncCount syncs, $errorCount errors\" -ForegroundColor DarkCyan
        
        # Wait
        Write-Host \"  Next sync in 60 seconds...\" -ForegroundColor DarkGray
        Start-Sleep -Seconds 60
    }
}

Monitor-Sync
"
