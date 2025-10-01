# ActivityWatch Sync Script - Using curl for HTTPS
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
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
            
            $jsonPayload = $payload | ConvertTo-Json -Depth 10 -Compress
            
            # Save JSON to temp file (curl works better with file input for large data)
            $tempFile = [System.IO.Path]::GetTempFileName()
            $jsonPayload | Out-File -FilePath $tempFile -Encoding UTF8 -NoNewline
            
            try {
                # Use curl.exe with -L to follow redirects
                $curlPath = "curl.exe"
                
                # Build curl command
                $curlArgs = @(
                    "-L",  # Follow redirects
                    "-X", "POST",
                    "-H", "Content-Type: application/json",
                    "-d", "@$tempFile",
                    "--max-time", "30",
                    "--silent",
                    "--show-error",
                    $SERVER_URL
                )
                
                # Execute curl
                $response = & $curlPath $curlArgs 2>&1
                $responseText = $response -join ""
                
                # Parse response
                try {
                    $responseObj = $responseText | ConvertFrom-Json
                    if ($responseObj.success) {
                        Write-Host "[SUCCESS] Synced $($allEvents.Count) events successfully" -ForegroundColor Green
                    } else {
                        Write-Host "Server error: $($responseObj.error)" -ForegroundColor Red
                    }
                } catch {
                    Write-Host "Response: $responseText" -ForegroundColor Yellow
                }
                
            } finally {
                # Clean up temp file
                Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
            }
        } else {
            Write-Host "No new data to sync"
        }
        
    } catch {
        Write-Host "Sync error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Check if curl is available
try {
    $curlVersion = & curl.exe --version 2>&1
    Write-Host "Using curl for HTTPS requests (handles redirects better)" -ForegroundColor Green
} catch {
    Write-Host "WARNING: curl.exe not found. This script requires curl." -ForegroundColor Red
    Write-Host "curl comes with Windows 10 version 1803 and later." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit
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