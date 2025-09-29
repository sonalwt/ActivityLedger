# ActivityWatch Sync Script - Using HTTP to avoid 308 redirect
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_bt91zeN3FMTmBZU2gN1AGIoUdHOM3h5srwHuo_yVoo0"
# Using HTTP to avoid 308 redirect
$SERVER_URL = "http://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

function Send-ActivityData {
    try {
        Write-Host "Checking ActivityWatch at $(Get-Date -Format 'HH:mm:ss')"

        # Test ActivityWatch connection first
        try {
            $testResponse = Invoke-RestMethod -Uri "$LOCAL_AW/info" -Method GET -TimeoutSec 5
        } catch {
            Write-Host "ActivityWatch is not running. Make sure it's started." -ForegroundColor Yellow
            return
        }

        # Get ActivityWatch buckets
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets/" -Method GET -TimeoutSec 10
        $buckets = $bucketsResponse.PSObject.Properties.Name | Where-Object { $_ -like "aw-*" }
        Write-Host "Found $($buckets.Count) ActivityWatch buckets"

        # Time range
        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddMinutes(-6)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")

        # Collect events
        $allEvents = @()
        foreach ($bucket in $buckets) {
            try {
                $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO"
                $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
                
                if ($events -and $events.Count -gt 0) {
                    $allEvents += $events
                    Write-Host "  - $bucket`: $($events.Count) events" -ForegroundColor DarkGray
                }
            } catch {
                # Skip buckets that error out
            }
        }

        if ($allEvents.Count -gt 0) {
            Write-Host "Sending $($allEvents.Count) total events to server..." -ForegroundColor Cyan
            
            # Prepare payload with token included
            $payload = @{
                name      = $DEVELOPER_NAME
                token     = $API_TOKEN
                data      = $allEvents
                timestamp = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            }
            
            $jsonPayload = $payload | ConvertTo-Json -Depth 10 -Compress
            
            # Send with proper headers
            $headers = @{
                "Content-Type" = "application/json"
                "Accept" = "application/json"
            }
            
            try {
                $response = Invoke-RestMethod -Uri $SERVER_URL -Method POST -Headers $headers -Body $jsonPayload -TimeoutSec 30
                
                if ($response.success) {
                    Write-Host "✓ Sync successful! Received $($response.received) activities" -ForegroundColor Green
                } elseif ($response.error) {
                    Write-Host "Server error: $($response.error)" -ForegroundColor Red
                } else {
                    Write-Host "✓ Data sent to server" -ForegroundColor Green
                }
            } catch {
                $statusCode = $_.Exception.Response.StatusCode.Value__
                
                if ($statusCode -eq 401 -or $statusCode -eq 403) {
                    Write-Host "Authentication failed. Check your API token." -ForegroundColor Red
                } else {
                    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
                }
            }
        } else {
            Write-Host "No new activity data to sync" -ForegroundColor Gray
        }
    } catch {
        Write-Host "Unexpected error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Main execution
Clear-Host
Write-Host "=========================================="
Write-Host "ActivityWatch Sync for $DEVELOPER_NAME" -ForegroundColor Cyan
Write-Host "Server: $SERVER_URL" -ForegroundColor Gray
Write-Host "=========================================="
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Initial sync
Send-ActivityData

# Continuous sync loop
while ($true) {
    $waitMinutes = 5
    $nextSync = (Get-Date).AddMinutes($waitMinutes).ToString("HH:mm:ss")
    
    for ($i = $waitMinutes * 60; $i -gt 0; $i--) {
        $minutes = [math]::Floor($i / 60)
        $seconds = $i % 60
        Write-Progress -Activity "Waiting for next sync" -Status "Next sync at $nextSync" -SecondsRemaining $i -PercentComplete ((($waitMinutes * 60) - $i) / ($waitMinutes * 60) * 100)
        Start-Sleep -Seconds 1
    }
    
    Write-Progress -Activity "Waiting for next sync" -Completed
    Send-ActivityData
}