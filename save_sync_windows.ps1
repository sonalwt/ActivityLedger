# Save sync.ps1 with proper Windows line endings
$content = @'
# ActivityWatch Sync Script - HTTPS with Redirect Handling
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
# Using HTTPS with proper redirect handling
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

function Send-ActivityData {
    try {
        Write-Host "$LOCAL_AW/buckets"
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets" -Method GET -TimeoutSec 10
        $buckets = $bucketsResponse.PSObject.Properties.Name
        Write-Host "Found $($buckets.Count) ActivityWatch buckets"
        
        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddMinutes(-6)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        
        $allEvents = @()
        foreach ($bucket in $buckets) {
            try {
                $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO"
                $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
                if ($events -and $events.Count -gt 0) {
                    $allEvents += $events
                    Write-Host ("  - " + $bucket + ": " + $events.Count + " events") -ForegroundColor DarkGray
                }
            } catch {
                # Skip bucket if error
            }
        }
        
        if ($allEvents.Count -gt 0) {
            Write-Host "Sending $($allEvents.Count) events to server..." -ForegroundColor Cyan
            
            $payload = @{
                name = $DEVELOPER_NAME
                token = $API_TOKEN  
                data = $allEvents
                timestamp = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            }
            
            $jsonPayload = $payload | ConvertTo-Json -Depth 10
            
            # Using Invoke-RestMethod with redirect handling
            try {
                $response = Invoke-RestMethod -Uri $SERVER_URL -Method POST -Body $jsonPayload -ContentType "application/json" -TimeoutSec 15 -MaximumRedirection 5
                
                if ($response.success) {
                    Write-Host "[SUCCESS] Synced $($allEvents.Count) events successfully" -ForegroundColor Green
                } else {
                    Write-Host "Server error: $($response.error)" -ForegroundColor Red
                }
            } catch {
                Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
            }
        } else {
            Write-Host "No new data to sync"
        }
        
    } catch {
        Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "========================================"
Write-Host "ActivityWatch Sync for $DEVELOPER_NAME"
Write-Host "Server: $SERVER_URL"
Write-Host "========================================"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

while ($true) {
    Send-ActivityData
    $nextSync = (Get-Date).AddMinutes(5).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "Waiting 5 minutes... (next sync at $nextSync)" -ForegroundColor DarkGray
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    Start-Sleep -Seconds 300
}
'@

# Save with Windows line endings
$content | Out-File -FilePath "C:\Users\ankit\Downloads\sync_windows.ps1" -Encoding UTF8

Write-Host "File saved to: C:\Users\ankit\Downloads\sync_windows.ps1"
Write-Host "This file has proper Windows line endings and UTF8 encoding."