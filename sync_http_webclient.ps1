# ActivityWatch Sync Script - Using HTTP as HTTPS redirects
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
# Based on testing, using HTTP endpoint to avoid 308 redirects
$SERVER_URL = "http://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

function Send-ActivityData {
    try {
        Write-Host "$LOCAL_AW/buckets"
        
        # Create web client with proper settings
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add("Content-Type", "application/json")
        
        # Get buckets
        $bucketsJson = $webClient.DownloadString("$LOCAL_AW/buckets")
        $bucketsResponse = $bucketsJson | ConvertFrom-Json
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
                $eventsJson = $webClient.DownloadString($eventsUrl)
                $events = $eventsJson | ConvertFrom-Json
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
            
            # Send to server
            try {
                $responseJson = $webClient.UploadString($SERVER_URL, $jsonPayload)
                $response = $responseJson | ConvertFrom-Json
                
                if ($response.success) {
                    Write-Host "[SUCCESS] Synced $($allEvents.Count) events successfully" -ForegroundColor Green
                } else {
                    Write-Host "Server error: $($response.error)" -ForegroundColor Red
                }
            } catch {
                Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
                if ($_.Exception.Message -like "*308*") {
                    Write-Host "Note: Server is redirecting. Contact administrator to fix server configuration." -ForegroundColor Yellow
                }
            }
        } else {
            Write-Host "No new data to sync"
        }
        
    } catch {
        Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
    } finally {
        if ($webClient) {
            $webClient.Dispose()
        }
    }
}

Write-Host "========================================"
Write-Host "ActivityWatch Sync for $DEVELOPER_NAME"
Write-Host "Server: $SERVER_URL"
Write-Host "========================================"
Write-Host "Note: Using HTTP endpoint due to HTTPS redirect issues" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop"
Write-Host ""

# Test connection first
Write-Host "Testing server connection..." -ForegroundColor Yellow
try {
    $testClient = New-Object System.Net.WebClient
    $testClient.Headers.Add("Content-Type", "application/json")
    $testPayload = '{"name":"test","token":"test","data":[],"timestamp":"2024-01-01T00:00:00Z"}'
    $testResponse = $testClient.UploadString($SERVER_URL, $testPayload)
    Write-Host "Server connection OK!" -ForegroundColor Green
} catch {
    if ($_.Exception.Message -like "*401*" -or $_.Exception.Message -like "*400*" -or $_.Exception.Message -like "*422*") {
        Write-Host "Server connection OK (auth error expected)!" -ForegroundColor Green
    } else {
        Write-Host "Warning: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} finally {
    if ($testClient) {
        $testClient.Dispose()
    }
}
Write-Host ""

while ($true) {
    Send-ActivityData
    $nextSync = (Get-Date).AddMinutes(5).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "Waiting 5 minutes... (next sync at $nextSync)" -ForegroundColor DarkGray
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    Start-Sleep -Seconds 300
}