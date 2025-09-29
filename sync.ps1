# ActivityWatch Sync Script - Updated
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
# FIXED: Changed from https:// to http:// to avoid 308 redirect
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

function Send-ActivityData {
    try {
        Write-Host "Checking ActivityWatch at $(Get-Date -Format 'HH:mm:ss')"

        # Get list of buckets
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets" -Method GET -TimeoutSec 10
        $buckets = $bucketsResponse.PSObject.Properties.Name
        Write-Host "Found $($buckets.Count) ActivityWatch buckets"

        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddMinutes(-$SYNC_INTERVAL)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO   = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")

        $allEvents = @()

        foreach ($bucket in $buckets) {
            try {
                $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO"
                $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
                if ($events -and $events.Count -gt 0) {
                    $allEvents += $events
                    Write-Host "  - $bucket: $($events.Count) events"
                }
            } catch {
                Write-Host "Warning: Could not get events from bucket $bucket" -ForegroundColor Yellow
            }
        }

        if ($allEvents.Count -gt 0) {
            Write-Host "Sending $($allEvents.Count) events to server..." -ForegroundColor Cyan

            $payload = @{
                name      = $DEVELOPER_NAME
                token     = $API_TOKEN
                data      = $allEvents
                timestamp = $endISO
            }

            $jsonPayload = $payload | ConvertTo-Json -Depth 10 -Compress

            # Send POST request with automatic redirect handling
            try {
                $response = Invoke-RestMethod -Uri $SERVER_URL `
                                              -Method POST `
                                              -Body $jsonPayload `
                                              -ContentType "application/json" `
                                              -MaximumRedirection 5 `
                                              -TimeoutSec 30

                if ($response.success) {
                    Write-Host "✓ Sync successful! ($($allEvents.Count) events)" -ForegroundColor Green
                } else {
                    Write-Host "Server returned: $($response.error)" -ForegroundColor Red
                }

            } catch {
                Write-Host "❌ Error sending data: $($_.Exception.Message)" -ForegroundColor Red
            }

        } else {
            Write-Host "No new activity data to sync" -ForegroundColor Gray
        }

    } catch {
        Write-Host "Unexpected error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# ===== MAIN LOOP =====
Clear-Host
Write-Host "============================================"
Write-Host "ActivityWatch Sync for $DEVELOPER_NAME" -ForegroundColor Cyan
Write-Host "Server: $SERVER_URL" -ForegroundColor Gray
Write-Host "Sync interval: $SYNC_INTERVAL minutes"
Write-Host "Press Ctrl+C to stop"
Write-Host "============================================`n"

# Initial sync
Send-ActivityData

# Continuous loop
while ($true) {
    Start-Sleep -Seconds ($SYNC_INTERVAL * 60)
    Send-ActivityData
}