# ActivityWatch Sync Script - Auto-detect working endpoint
$DEVELOPER_NAME = "ankita gholap"
$API_TOKEN = "AWToken_sFM_KiPpk3fuK64zdgGD-kWoZZf4MLlDeuY0nF8OyTs"
$LOCAL_AW = "http://localhost:5600/api/0"

# Test different endpoints to find one that works
Write-Host "Testing endpoints to find working URL..." -ForegroundColor Yellow
$endpoints = @(
    "https://api-timesheet.firsteconomy.com/api/sync",
    "https://api-timesheet.firsteconomy.com/api/sync/",
    "http://api-timesheet.firsteconomy.com/api/sync",
    "http://api-timesheet.firsteconomy.com/api/sync/"
)

$SERVER_URL = ""
$testPayload = '{"name":"test","token":"test","data":[],"timestamp":"2024-01-01T00:00:00Z"}'

foreach ($endpoint in $endpoints) {
    Write-Host "Testing: $endpoint" -ForegroundColor Cyan
    try {
        $response = Invoke-WebRequest -Uri $endpoint -Method POST -Body $testPayload -ContentType "application/json" -UseBasicParsing -ErrorAction Stop
        Write-Host "  Success! Using this endpoint." -ForegroundColor Green
        $SERVER_URL = $endpoint
        break
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 400 -or $statusCode -eq 422 -or $statusCode -eq 401) {
            Write-Host "  Success! Endpoint responds correctly (error $statusCode is expected for test data)." -ForegroundColor Green
            $SERVER_URL = $endpoint
            break
        } elseif ($statusCode -eq 308) {
            Write-Host "  308 Redirect - trying next..." -ForegroundColor Yellow
        } else {
            Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

if ($SERVER_URL -eq "") {
    Write-Host "ERROR: No working endpoint found!" -ForegroundColor Red
    Write-Host "Please contact your administrator." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit
}

Write-Host ""
Write-Host "Using endpoint: $SERVER_URL" -ForegroundColor Green
Write-Host ""

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
            
            # Use Invoke-WebRequest instead of Invoke-RestMethod for better control
            try {
                $response = Invoke-WebRequest -Uri $SERVER_URL -Method POST -Body $jsonPayload -ContentType "application/json" -UseBasicParsing
                $responseContent = $response.Content | ConvertFrom-Json
                
                if ($responseContent.success) {
                    Write-Host "[SUCCESS] Synced $($allEvents.Count) events successfully" -ForegroundColor Green
                } else {
                    Write-Host "Server error: $($responseContent.error)" -ForegroundColor Red
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