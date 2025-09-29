# sync_follow_redirects.ps1
# ActivityWatch Sync Script - Follows redirects automatically
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_bt91zeN3FMTmBZU2gN1AGIoUdHOM3h5srwHuo_yVoo0"
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

# Enable TLS 1.2 for HTTPS
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Send-ActivityData {
    try {
        Write-Host "Checking ActivityWatch at $(Get-Date -Format 'HH:mm:ss')"

        # Test ActivityWatch connection
        try {
            $testResponse = Invoke-WebRequest -Uri "$LOCAL_AW/info" -Method GET -TimeoutSec 5 -UseBasicParsing
        } catch {
            Write-Host "ActivityWatch is not running. Make sure it's started." -ForegroundColor Yellow
            return
        }

        # Get buckets
        $bucketsJson = (Invoke-WebRequest -Uri "$LOCAL_AW/buckets" -Method GET -TimeoutSec 10 -UseBasicParsing).Content
        $buckets = ($bucketsJson | ConvertFrom-Json).PSObject.Properties.Name | Where-Object { $_ -like "aw-*" }
        Write-Host "Found $($buckets.Count) ActivityWatch buckets"

        # Time range
        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddMinutes(-5)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")

        # Collect events
        $allEvents = @()
        foreach ($bucket in $buckets) {
            try {
                $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO"
                $eventsJson = (Invoke-WebRequest -Uri $eventsUrl -Method GET -TimeoutSec 10 -UseBasicParsing).Content
                $events = $eventsJson | ConvertFrom-Json
                
                if ($events -and $events.Count -gt 0) {
                    $allEvents += $events
                    Write-Host "  - $bucket`: $($events.Count) events" -ForegroundColor DarkGray
                }
            } catch {
                # Skip problematic buckets
            }
        }

        if ($allEvents.Count -gt 0) {
            Write-Host "Sending $($allEvents.Count) events..." -ForegroundColor Cyan
            
            $payload = @{
                name      = $DEVELOPER_NAME
                token     = $API_TOKEN
                data      = $allEvents
                timestamp = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            }
            
            $jsonPayload = $payload | ConvertTo-Json -Depth 10 -Compress
            
            # Use Invoke-WebRequest with automatic redirect following
            try {
                # This will follow redirects automatically (including 308)
                $response = Invoke-WebRequest `
                    -Uri $SERVER_URL `
                    -Method POST `
                    -ContentType "application/json" `
                    -Body $jsonPayload `
                    -TimeoutSec 30 `
                    -UseBasicParsing `
                    -MaximumRedirection 5  # Follow up to 5 redirects
                
                $responseData = $response.Content | ConvertFrom-Json
                
                if ($responseData.success) {
                    Write-Host "✓ Sync successful!" -ForegroundColor Green
                } else {
                    Write-Host "Server returned: $($responseData.error)" -ForegroundColor Red
                }
                
                # Show if we were redirected
                if ($response.BaseResponse.ResponseUri.ToString() -ne $SERVER_URL) {
                    Write-Host "Note: Request was redirected to: $($response.BaseResponse.ResponseUri)" -ForegroundColor Yellow
                }
                
            } catch {
                Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
                if ($_.Exception.Response) {
                    $statusCode = [int]$_.Exception.Response.StatusCode
                    Write-Host "Status Code: $statusCode" -ForegroundColor Red
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
Write-Host "ActivityWatch Sync (with redirect handling)" -ForegroundColor Cyan
Write-Host "Developer: $DEVELOPER_NAME" -ForegroundColor Gray
Write-Host "=========================================="
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Initial sync
Send-ActivityData

# Continuous sync
while ($true) {
    Start-Sleep -Seconds 300
    Send-ActivityData
}