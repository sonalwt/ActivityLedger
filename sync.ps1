# ActivityWatch Sync Script - Generated for ankita gholap
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "https://localhost:5600/api/0"

function Send-ActivityData {
    try {
        Write-Host "Checking ActivityWatch at $(Get-Date -Format 'HH:mm:ss')"
        
        # Get ActivityWatch buckets
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets" -Method GET -TimeoutSec 10
        $buckets = $bucketsResponse.PSObject.Properties.Name
        
        Write-Host "Found $($buckets.Count) ActivityWatch buckets"
        
        # Calculate time range (last 6 minutes)
        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddMinutes(-6)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        
        # Collect all events
        $allEvents = @()
        foreach ($bucket in $buckets) {
            try {
                $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO"
                $events = Invoke-RestMethod -Uri $eventsUrl -Method GET -TimeoutSec 10
                $allEvents += $events
            }
            catch {
                Write-Host "Warning: Could not get events from bucket $bucket"
            }
        }
        
        if ($allEvents.Count -gt 0) {
            # Prepare payload
            $payload = @{
                name = $DEVELOPER_NAME
                token = $API_TOKEN  
                data = $allEvents
                timestamp = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            }
            
            # Send to server
            $jsonPayload = $payload | ConvertTo-Json -Depth 10 -Compress
            $response = Invoke-RestMethod -Uri $SERVER_URL -Method POST -Body $jsonPayload -ContentType "application/json" -TimeoutSec 15
            
            if ($response.success) {
                Write-Host "Synced $($allEvents.Count) events successfully" -ForegroundColor Green
            }
            else {
                Write-Host "Server error: $($response.error)" -ForegroundColor Red
            }
        }
        else {
            Write-Host "No new data to sync"
        }
    }
    catch {
        Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Main execution
Write-Host "=========================================="
Write-Host "ActivityWatch Sync for $DEVELOPER_NAME" -ForegroundColor Cyan
Write-Host "=========================================="
Write-Host "Press Ctrl+C to stop"
Write-Host ""

# Continuous sync loop
while ($true) {
    Send-ActivityData
    $nextSync = (Get-Date).AddMinutes(5).ToString("HH:mm:ss")
    Write-Host "Waiting 5 minutes... (next sync at $nextSync)"
    Start-Sleep -Seconds 300
}