# ActivityWatch Sync Script - PowerShell Version
# No Python installation required!

# CHANGE THESE VALUES:
const syncPsContent = `# ActivityWatch Sync Script - Generated for ${developerName}
$DEVELOPER_NAME = "${developerName}"
$API_TOKEN = "${apiToken}"
# Don't change below this line
$SERVER_URL = "http://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

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
            } catch {
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
            $jsonPayload = $payload | ConvertTo-Json -Depth 10
            # $response = Invoke-RestMethod -Uri $SERVER_URL -Method POST -Body $jsonPayload -ContentType "application/json" -TimeoutSec 15
            try {
                $response = Invoke-RestMethod -Uri $SERVER_URL -Method POST -Body $jsonPayload -ContentType "application/json" -TimeoutSec 15
            } catch {
                if ($_.Exception.Response.StatusCode.Value__ -eq 308) {
                    $redirectUrl = $_.Exception.Response.Headers["Location"]
                    Write-Host "Redirect detected, resending to $redirectUrl"
                    $response = Invoke-RestMethod -Uri $redirectUrl -Method POST -Body $jsonPayload -ContentType "application/json" -TimeoutSec 15
                } else {
                    throw $_
                }
            }
            if ($response.success) {
                Write-Host "✓ Synced $($allEvents.Count) events successfully" -ForegroundColor Green
            } else {
                Write-Host "✗ Server error: $($response.error)" -ForegroundColor Red
            }
        } else {
            Write-Host "No new data to sync"
        }
        
    } catch {
        Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Main execution
Write-Host "=" * 50
Write-Host "ActivityWatch Sync for $DEVELOPER_NAME" -ForegroundColor Cyan
Write-Host "=" * 50
Write-Host "Press Ctrl+C to stop"
Write-Host ""

# Continuous sync loop
while ($true) {
    Send-ActivityData
    $nextSync = (Get-Date).AddMinutes(5).ToString("HH:mm:ss")
    Write-Host "Waiting 5 minutes... (next sync at $nextSync)"
    Start-Sleep -Seconds 300  # 5 minutes
}
