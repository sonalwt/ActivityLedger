# ActivityWatch Sync Script - HTTPS with proper handling
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_bt91zeN3FMTmBZU2gN1AGIoUdHOM3h5srwHuo_yVoo0"
$SERVER_URL = "https://api-timesheet.firsteconomy.com/api/sync"
$LOCAL_AW = "http://localhost:5600/api/0"

# Force TLS 1.2 for HTTPS
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Sync interval in minutes
$SYNC_INTERVAL = 5

function Send-ActivityData {
    try {
        Write-Host "Checking ActivityWatch at $(Get-Date -Format 'HH:mm:ss')"

        # Test ActivityWatch connection
        try {
            $testResponse = Invoke-RestMethod -Uri "$LOCAL_AW/info" -Method GET -TimeoutSec 5
        } catch {
            Write-Host "ActivityWatch is not running. Make sure it's started." -ForegroundColor Yellow
            return
        }

        # Get ActivityWatch buckets
        $bucketsResponse = Invoke-RestMethod -Uri "$LOCAL_AW/buckets" -Method GET -TimeoutSec 10
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
            
            # Prepare payload
            $payload = @{
                name      = $DEVELOPER_NAME
                token     = $API_TOKEN
                data      = $allEvents
                timestamp = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            }
            
            $jsonPayload = $payload | ConvertTo-Json -Depth 10 -Compress
            
            # Use WebRequest to handle redirects properly
            try {
                # Create web request with redirect handling
                $webRequest = [System.Net.HttpWebRequest]::Create($SERVER_URL)
                $webRequest.Method = "POST"
                $webRequest.ContentType = "application/json"
                $webRequest.AllowAutoRedirect = $true
                $webRequest.MaximumAutomaticRedirections = 5
                
                # Write data
                $bytes = [System.Text.Encoding]::UTF8.GetBytes($jsonPayload)
                $webRequest.ContentLength = $bytes.Length
                $requestStream = $webRequest.GetRequestStream()
                $requestStream.Write($bytes, 0, $bytes.Length)
                $requestStream.Close()
                
                # Get response
                try {
                    $webResponse = $webRequest.GetResponse()
                    $responseStream = $webResponse.GetResponseStream()
                    $reader = New-Object System.IO.StreamReader($responseStream)
                    $responseText = $reader.ReadToEnd()
                    $reader.Close()
                    
                    $response = $responseText | ConvertFrom-Json
                    
                    if ($response.success) {
                        Write-Host "✓ Sync successful!" -ForegroundColor Green
                    } else {
                        Write-Host "Server response: $responseText" -ForegroundColor Yellow
                    }
                    
                    # Check if we were redirected
                    if ($webResponse.ResponseUri.ToString() -ne $SERVER_URL) {
                        Write-Host "Note: Redirected to: $($webResponse.ResponseUri)" -ForegroundColor DarkGray
                    }
                    
                } catch [System.Net.WebException] {
                    $errorResponse = $_.Exception.Response
                    if ($errorResponse) {
                        $statusCode = [int]$errorResponse.StatusCode
                        Write-Host "HTTP Error $statusCode`: $($errorResponse.StatusDescription)" -ForegroundColor Red
                        
                        if ($statusCode -eq 308) {
                            Write-Host "Still getting 308 redirect. Checking redirect location..." -ForegroundColor Yellow
                            $redirectLocation = $errorResponse.Headers["Location"]
                            if ($redirectLocation) {
                                Write-Host "Redirect location: $redirectLocation" -ForegroundColor Yellow
                                Write-Host "Update your SERVER_URL to: $redirectLocation" -ForegroundColor Yellow
                            }
                        }
                    }
                }
                
            } catch {
                Write-Host "Request error: $($_.Exception.Message)" -ForegroundColor Red
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
Write-Host "Using HTTPS with redirect handling" -ForegroundColor Gray
Write-Host "=========================================="
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Initial sync
Send-ActivityData

# Continuous sync loop
while ($true) {
    $waitMinutes = $SYNC_INTERVAL
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