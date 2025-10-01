# ActivityWatch Sync - Using Windows curl.exe
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
$LOCAL_AW = "http://localhost:5600/api/0"

# Test which URL works
Write-Host "Testing server endpoints with curl..." -ForegroundColor Yellow

$endpoints = @(
    "http://api-timesheet.firsteconomy.com/api/sync",
    "http://api-timesheet.firsteconomy.com/api/sync/",
    "https://api-timesheet.firsteconomy.com/api/sync",
    "https://api-timesheet.firsteconomy.com/api/sync/"
)

$SERVER_URL = ""
$testJson = '{"name":"test","token":"test","data":[],"timestamp":"2024-01-01T00:00:00Z"}'

foreach ($url in $endpoints) {
    Write-Host "`nTesting: $url"
    $result = curl.exe -s -X POST -H "Content-Type: application/json" -d $testJson -w "`nHTTP_CODE:%{http_code}" -L $url 2>&1
    $output = $result -join ""
    
    if ($output -match "HTTP_CODE:([0-9]+)") {
        $httpCode = $matches[1]
        Write-Host "  Response code: $httpCode" -ForegroundColor Cyan
        
        if ($httpCode -eq "200" -or $httpCode -eq "400" -or $httpCode -eq "401" -or $httpCode -eq "422") {
            Write-Host "  ✅ This endpoint works!" -ForegroundColor Green
            $SERVER_URL = $url
            break
        }
    }
}

if ($SERVER_URL -eq "") {
    Write-Host "`n❌ No working endpoint found!" -ForegroundColor Red
    Write-Host "Please check with your server administrator." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit
}

Write-Host "`nUsing endpoint: $SERVER_URL" -ForegroundColor Green
Write-Host ""

function Send-ActivityData {
    try {
        Write-Host "Checking ActivityWatch..." -ForegroundColor Gray
        
        # Get buckets using curl
        $bucketsJson = curl.exe -s "$LOCAL_AW/buckets" 2>&1 | Out-String
        $buckets = ($bucketsJson | ConvertFrom-Json).PSObject.Properties.Name
        Write-Host "Found $($buckets.Count) ActivityWatch buckets"
        
        $endTime = (Get-Date).ToUniversalTime()
        $startTime = $endTime.AddMinutes(-6)
        $startISO = $startTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $endISO = $endTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        
        $allEvents = @()
        foreach ($bucket in $buckets) {
            $eventsUrl = "$LOCAL_AW/buckets/$bucket/events?start=$startISO&end=$endISO"
            $eventsJson = curl.exe -s $eventsUrl 2>&1 | Out-String
            
            try {
                $events = $eventsJson | ConvertFrom-Json
                if ($events -and $events.Count -gt 0) {
                    $allEvents += $events
                    Write-Host ("  - " + $bucket + ": " + $events.Count + " events") -ForegroundColor DarkGray
                }
            } catch {
                # Skip if parse error
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
            
            # Save to temp file (curl handles files better)
            $tempFile = [System.IO.Path]::GetTempFileName()
            $jsonPayload | Out-File -FilePath $tempFile -Encoding UTF8 -NoNewline
            
            try {
                # Use curl with -L to follow redirects
                $response = curl.exe -s -L -X POST -H "Content-Type: application/json" -d "@$tempFile" $SERVER_URL 2>&1 | Out-String
                
                try {
                    $responseObj = $response | ConvertFrom-Json
                    if ($responseObj.success) {
                        Write-Host "[SUCCESS] Synced $($allEvents.Count) events successfully" -ForegroundColor Green
                    } else {
                        Write-Host "Server error: $($responseObj.error)" -ForegroundColor Red
                    }
                } catch {
                    Write-Host "Response: $response" -ForegroundColor Yellow
                }
                
            } finally {
                Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
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
Write-Host "Using curl.exe for better redirect handling"
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